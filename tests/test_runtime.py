from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_ROOT = REPO_ROOT / "codex"
if str(CODEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CODEX_ROOT))

from hooks.core.controller import process_turn
from hooks.redteam_state import RedTeamState
from runtime import (
    DurableStore,
    GoalCompiler,
    OperationState,
    TerminalJudge,
    ToolBroker,
    WorkflowRegistry,
    WorkflowSpec,
)


def _operation(tmp_path: Path) -> tuple[DurableStore, OperationState, WorkflowSpec]:
    registry = WorkflowRegistry()
    goal = GoalCompiler().compile("Validate SQL injection on https://target.invalid")
    workflow = registry.match(goal)
    state = OperationState.create(session_id="runtime-test", goal=goal, workflow=workflow)
    store = DurableStore(tmp_path / "operations")
    store.create_operation(state, event={"source": "pytest"})
    return store, state, workflow


def test_goal_compiler_matches_the_unified_adaptive_workflow() -> None:
    registry = WorkflowRegistry()
    workflows = registry.load(refresh=True)
    goal = GoalCompiler().compile("Validate SQL injection on https://target.invalid")

    assert len(workflows) == 1
    assert goal.targets == ("https://target.invalid",)
    assert goal.workflow_hint == "generic-adaptive"
    assert registry.match(goal).workflow_id == "generic-adaptive"
    assert all(criterion.target == "https://target.invalid" for criterion in goal.success_criteria)


def test_durable_store_round_trips_operation_state_and_events(tmp_path: Path) -> None:
    store, state, _ = _operation(tmp_path)

    loaded = store.load_operation(state.run_id)
    latest = store.latest_operation(state.session_id)
    events = store.events(state.run_id)

    assert loaded is not None
    assert loaded.run_id == state.run_id
    assert loaded.goal.to_dict() == state.goal.to_dict()
    assert loaded.workflow_id == state.workflow_id
    assert loaded.action_status == state.action_status
    assert latest is not None and latest.run_id == state.run_id
    assert [event["event_type"] for event in events] == ["operation_started"]


def test_terminal_judge_requires_verified_target_evidence(tmp_path: Path) -> None:
    _, state, workflow = _operation(tmp_path)

    decision = TerminalJudge().evaluate(
        state=state,
        goal=state.goal,
        workflow=workflow,
        evidence=(),
    )

    assert decision.terminal is False
    assert decision.success is False
    assert decision.reason == "goal_predicates_pending"
    assert f"target_evidence:{state.goal.targets[0]}" in decision.missing


def test_tool_broker_selects_capability_and_validates_arguments() -> None:
    broker = ToolBroker()
    fallback = broker.register_adapter(
        name="fallback-fetch",
        capabilities=("http_request",),
        adapter=lambda arguments: {"target": arguments["target"]},
        priority=20,
        input_schema={
            "type": "object",
            "required": ["target"],
            "properties": {"target": {"type": "string"}},
            "additionalProperties": False,
        },
    )
    preferred = broker.register_adapter(
        name="preferred-fetch",
        capabilities=("http_request",),
        adapter=lambda arguments: {"target": arguments["target"]},
        priority=10,
        input_schema={
            "type": "object",
            "required": ["target"],
            "properties": {"target": {"type": "string"}},
            "additionalProperties": False,
        },
    )

    assert broker.select(("http_request",)) == preferred
    assert broker.select(("http_request",), exclude=(preferred.qualified_name,)) == fallback
    assert broker.call(preferred, {}).error == "tool_schema_required_missing:target"
    result = broker.call(preferred, {"target": "https://target.invalid"})
    assert result.status == "success"
    assert result.output == {"target": "https://target.invalid"}


@pytest.mark.parametrize(
    ("automation_mode", "expected_status", "expected_next_action"),
    [("plan-only", "planned", ""), ("active", "dispatch_pending", "redteam_run")],
)
def test_process_turn_respects_automation_mode(
    monkeypatch: pytest.MonkeyPatch,
    automation_mode: str,
    expected_status: str,
    expected_next_action: str,
) -> None:
    monkeypatch.setenv("CODEX_REDTEAM_AUTOMATION_MODE", automation_mode)
    state = RedTeamState(mode="redteam-light", session_id="controller-test")

    result = process_turn(
        prompt="Validate SQL injection on https://target.invalid",
        state=state,
        codex_dir=CODEX_ROOT,
    )

    assert result.state.operation_status == expected_status
    assert result.state.next_action_id == expected_next_action
    assert f"[automation-mode:{automation_mode}]" in result.brief
    assert bool(result.state.pending_action) is (automation_mode == "active")


def test_proxy_mode_dispatch_uses_normalized_objective_without_raw_clause_text(tmp_path: Path) -> None:
    codex_dir = tmp_path / "codex"
    codex_dir.mkdir()
    (codex_dir / "config.toml").write_text(
        '''[automation]
mode = "active"
[redteam.prompt_rewrite]
mode = "proxy"
''',
        encoding="utf-8",
    )
    state = RedTeamState(mode="redteam-light", session_id="proxy-controller")
    prompt = "验证 https://target.invalid/login 的 SQL 注入并输出 PoC"

    result = process_turn(prompt=prompt, state=state, codex_dir=codex_dir)

    assert "SQL 注入" not in result.overlay
    assert "数据库查询构造边界验证" in result.overlay
    assert "https://target.invalid/login" in result.overlay
    metadata = result.state.pending_action["starting_context"]["prompt_rewrite"]
    assert all("text" not in clause for clause in metadata["clauses"])
    assert all(clause["sha256"] for clause in metadata["clauses"])
    assert metadata["taxonomy"] == ["CWE-89"]
    assert {"evidence", "validation"} <= set(metadata["context_bundle"])


def test_ordinary_development_does_not_dispatch_redteam_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_REDTEAM_AUTOMATION_MODE", "active")
    state = RedTeamState(mode="redteam-light", session_id="ordinary-development")

    result = process_turn(
        prompt="优化这段 SQL 查询，减少全表扫描并修复参数绑定问题",
        state=state,
        codex_dir=CODEX_ROOT,
    )

    assert result.reason_code == "ordinary-development"
    assert result.state.pending_action == {}
    assert result.state.next_action_id == ""
    assert "[security-context:false]" in result.brief


def test_ordinary_development_detour_preserves_pending_redteam_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_REDTEAM_AUTOMATION_MODE", "active")
    state = RedTeamState(
        mode="redteam-light",
        session_id="ordinary-detour",
        objective="验证既有目标",
        operation_run_id="run-existing",
        pending_action={"dispatch": "redteam_run", "run_id": "run-existing"},
        last_scene="vuln",
        last_action_kind="verify",
        last_risk_level="research",
        last_context_bundle=["defensive_analysis", "evidence", "validation"],
    )

    result = process_turn(
        prompt="优化这段 SQL 查询并减少全表扫描",
        state=state,
        codex_dir=CODEX_ROOT,
    )

    assert result.reason_code == "ordinary-development"
    assert result.state.pending_action == state.pending_action
    assert result.state.last_scene == "vuln"
    assert result.state.last_action_kind == "verify"


def test_runtime_mcp_server_lists_operation_tools(tmp_path: Path) -> None:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    env = {**os.environ, "PYTHONPATH": str(CODEX_ROOT)}

    completed = subprocess.run(
        [sys.executable, "-m", "runtime.mcp_server", "--root", str(tmp_path / "operations")],
        input="\n".join(json.dumps(item) for item in requests) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=env,
        check=False,
    )

    responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    initialize_response = next(item for item in responses if item.get("id") == 1)
    tool_response = next(item for item in responses if item.get("id") == 2)
    initialize_result = initialize_response["result"]
    tools = tool_response["result"]["tools"]
    names = {item["name"] for item in tools}
    assert completed.returncode == 0
    assert initialize_result["protocolVersion"] == "2025-06-18"
    assert initialize_result["capabilities"] == {"tools": {"listChanged": False}}
    assert initialize_result["serverInfo"]["name"] == "codex-redteam-runtime"
    assert {"redteam_run", "redteam_status", "redteam_cancel"} <= names

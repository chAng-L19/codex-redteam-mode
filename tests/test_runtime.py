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


def test_goal_compiler_matches_one_of_eight_typed_workflows() -> None:
    registry = WorkflowRegistry()
    workflows = registry.load(refresh=True)
    goal = GoalCompiler().compile("Validate SQL injection on https://target.invalid")

    assert len(workflows) == 8
    assert goal.targets == ("https://target.invalid",)
    assert goal.workflow_hint == "web-api-assessment"
    assert registry.match(goal).workflow_id == "web-api-assessment"
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

from __future__ import annotations

import json
import os
import tomllib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime import GoalCompiler, WorkflowRegistry

try:
    from redteam_state import RedTeamState
except ModuleNotFoundError:
    from hooks.redteam_state import RedTeamState

from .intent_engine import IntentDecision, detect_intent


ACTIVE_AUTOMATION_MODES = {"active", "auto", "assisted", "execute", "execution"}
PLAN_ONLY_AUTOMATION_MODES = {"off", "false", "0", "plan", "plan-only", "plan_only", "dry-run"}


@dataclass
class ProcessTurnResult:
    state: RedTeamState
    brief: str
    overlay: str
    artifact: object | None
    reason_code: str


def _configs(codex_dir: Path) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    explicit = os.environ.get("CODEX_REDTEAM_CONFIG", "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend((codex_dir / "config.toml", codex_dir.parent / "config.toml"))
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    candidates.append(Path(codex_home).expanduser() / "config.toml" if codex_home else Path.home() / ".codex" / "config.toml")
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).casefold()
        if key in seen or not candidate.is_file():
            continue
        seen.add(key)
        try:
            payload = tomllib.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if isinstance(payload, dict):
            resolved.append(payload)
    return resolved


def _automation_mode(codex_dir: Path, redteam_mode: str) -> str:
    if redteam_mode not in {"redteam-light", "redteam-full"}:
        return "plan-only"
    environment = os.environ.get("CODEX_REDTEAM_AUTOMATION_MODE", "").strip().casefold()
    if environment:
        return "active" if environment in ACTIVE_AUTOMATION_MODES else "plan-only"
    for config in _configs(codex_dir):
        features = config.get("features") if isinstance(config.get("features"), dict) else {}
        automation = config.get("automation") if isinstance(config.get("automation"), dict) else {}
        if features.get("automation") is False:
            return "plan-only"
        configured = str(automation.get("mode") or "").strip().casefold()
        if configured in ACTIVE_AUTOMATION_MODES:
            return "active"
        if configured in PLAN_ONLY_AUTOMATION_MODES:
            return "plan-only"
    return "active"


def _automation_mode_from_config(codex_home: Path, redteam_mode: str) -> str:
    """Compatibility wrapper retained for installer/runtime validation callers."""
    return _automation_mode(codex_home, redteam_mode)


def _rewrite_mode(codex_dir: Path) -> str:
    environment = os.environ.get("CODEX_REDTEAM_PROMPT_REWRITE_MODE", "").strip().casefold()
    if environment:
        return environment
    for config in _configs(codex_dir):
        redteam = config.get("redteam") if isinstance(config.get("redteam"), dict) else {}
        rewrite = redteam.get("prompt_rewrite") if isinstance(redteam.get("prompt_rewrite"), dict) else {}
        mode = str(rewrite.get("mode") or "").strip().casefold()
        if mode:
            return mode
    return "context"


def _terminal_result(working: RedTeamState, intent: IntentDecision) -> ProcessTurnResult:
    working.intent_type = intent.intent_type
    working.operation_status = "completed" if working.goal_success else working.operation_status
    working.next_action_id = ""
    working.pending_action = {}
    brief = "\n".join(
        (
            f"[workflow:{working.workflow_id or 'generic-adaptive'}]",
            f"[operation-status:{working.operation_status or 'terminal'}]",
            "[goal-terminal:true]",
            f"[goal-success:{str(working.goal_success).lower()}]",
            "[feedback-gate:semantic-terminal-judge]",
            "[exit-condition:goal-contract-satisfied]",
            "[next-action:none]",
        )
    )
    reference = (
        f"batch_session_id={working.batch_session_id!r}"
        if working.batch_session_id
        else f"run_id={working.operation_run_id!r}"
    )
    return ProcessTurnResult(
        state=working,
        brief=brief,
        overlay=f"[operation-terminal] Preserve the proven terminal state; retrieve evidence with redteam_run using {reference}.",
        artifact=None,
        reason_code="terminal",
    )


def _resume_call(working: RedTeamState) -> dict[str, Any] | None:
    pending = working.pending_action if isinstance(working.pending_action, dict) else {}
    batch_session_id = str(pending.get("batch_session_id") or working.batch_session_id or "").strip()
    if batch_session_id:
        return {"batch_session_id": batch_session_id}
    run_id = str(pending.get("run_id") or working.operation_run_id or "").strip()
    return {"run_id": run_id} if run_id else None


def _dispatch_overlay(call: dict[str, Any], rewrite_context: str = "") -> str:
    prefix = f"{rewrite_context}\n" if rewrite_context else ""
    return (
        f"{prefix}[operation-dispatch] Call redteam_run with this JSON: "
        f"{json.dumps(call, ensure_ascii=False)}. Continue until a terminal result or a pending host-only action. "
        "For a host-only action, execute next_action_spec with current Codex tools and submit the observation through "
        "redteam_run. Do not ask the user to relay tool output."
    )


def _remember_rewrite(state: RedTeamState, rewrite: object | None) -> None:
    if rewrite is None:
        return
    state.last_scene = str(getattr(rewrite, "scene", "") or "")
    state.last_action_kind = str(getattr(rewrite, "action_kind", "") or "")
    state.last_risk_level = str(getattr(rewrite, "risk_level", "") or "")
    state.last_context_bundle = list(getattr(rewrite, "context_bundle", ()) or ())
    state.last_taxonomy = list(getattr(rewrite, "taxonomy", ()) or ())


def _ordinary_development_result(working: RedTeamState, intent: IntentDecision) -> ProcessTurnResult:
    """Keep ordinary development prompts out of the red-team dispatch loop."""
    working.intent_type = intent.intent_type
    if not working.objective and not working.operation_run_id and not working.pending_action:
        working.operation_status = "ordinary-development"
    working.next_action_id = ""
    return ProcessTurnResult(
        state=working,
        brief="\n".join(
            (
                "[routing:ordinary-development]",
                "[security-context:false]",
                "[workflow:none]",
                "[next-action:none]",
            )
        ),
        overlay=(
            "[ordinary-development] Handle this turn as a normal engineering task. "
            "Do not start or resume the red-team operation unless the user supplies a new security objective."
        ),
        artifact=None,
        reason_code="ordinary-development",
    )


def process_turn(
    *,
    prompt: str,
    state: RedTeamState,
    codex_dir: Path,
    assistant_summary: str = "",
) -> ProcessTurnResult:
    del assistant_summary
    working = deepcopy(state).normalized()
    intent = detect_intent(prompt, working)
    if intent.rewrite is not None and intent.rewrite.ordinary_dev:
        return _ordinary_development_result(working, intent)
    _remember_rewrite(working, intent.rewrite)
    if working.goal_terminal and intent.intent_type not in {"new", "revise"}:
        return _terminal_result(working, intent)

    automation_mode = _automation_mode(codex_dir, working.mode)
    rewrite_mode = _rewrite_mode(codex_dir)
    proxy_rewrite = rewrite_mode == "proxy"
    rewrite_context = (
        intent.rewrite.render_context()
        if intent.rewrite is not None and rewrite_mode not in {"off", "false", "0", "proxy"}
        else ""
    )
    resume_call = _resume_call(working)
    if resume_call and intent.intent_type in {"continue", "verify", "summarize"}:
        working.intent_type = intent.intent_type
        working.workflow_id = working.workflow_id or "generic-adaptive"
        working.operation_status = "dispatch_pending" if automation_mode == "active" else "planned"
        working.next_action_id = "redteam_run" if automation_mode == "active" else ""
        working.pending_action = {"dispatch": "redteam_run", **resume_call} if automation_mode == "active" else {}
        brief = "\n".join(
            (
                "[workflow:generic-adaptive]",
                f"[operation-status:{working.operation_status}]",
                f"[automation-mode:{automation_mode}]",
                "[goal-terminal:false]",
                "[feedback-gate:semantic-terminal-judge]",
                f"[next-action:{working.next_action_id or 'none'}]",
            )
        )
        overlay = _dispatch_overlay(resume_call, rewrite_context) if automation_mode == "active" else "[operation-plan] Resume is disabled by plan-only automation mode."
        return ProcessTurnResult(working, brief, overlay, None, working.operation_status)

    if not working.objective or intent.intent_type in {"new", "revise"}:
        working.objective = intent.objective_delta or prompt.strip()
        working.operation_run_id = ""
        working.operation_run_ids = []
        working.batch_session_id = ""
        working.pending_action = {}
        working.workflow_terminal = False
        working.goal_terminal = False
        working.goal_success = False

    starting_context = (
        {"prompt_rewrite": intent.rewrite.to_dict(include_clause_text=not proxy_rewrite)}
        if intent.rewrite is not None
        else {}
    )
    runtime_objective = (
        intent.rewrite.research_brief
        if proxy_rewrite and intent.rewrite is not None
        else working.objective or prompt.strip()
    )
    goal = GoalCompiler().compile(runtime_objective, starting_context=starting_context)
    workflow = WorkflowRegistry().get()
    call = {
        "session_id": working.session_id or "default",
        "objective": goal.objective,
        "targets": list(goal.targets),
        "workflow_hint": "generic-adaptive",
        "starting_context": dict(goal.starting_context),
        "constraints": {"opsec_level": working.opsec_level},
    }
    working.intent_type = intent.intent_type
    working.workflow_id = workflow.workflow_id
    working.operation_status = "dispatch_pending" if automation_mode == "active" else "planned"
    working.next_action_id = "redteam_run" if automation_mode == "active" else ""
    working.pending_action = {"dispatch": "redteam_run", **call} if automation_mode == "active" else {}
    brief = "\n".join(
        (
            "[workflow:generic-adaptive]",
            f"[operation-status:{working.operation_status}]",
            f"[automation-mode:{automation_mode}]",
            "[goal-terminal:false]",
            "[goal-success:false]",
            "[feedback-gate:semantic-terminal-judge]",
            "[exit-condition:goal-contract-satisfied]",
            f"[targets:{','.join(goal.targets) or 'missing'}]",
            f"[next-action:{working.next_action_id or 'none'}]",
        )
    )
    overlay = (
        _dispatch_overlay(call, rewrite_context)
        if automation_mode == "active"
        else "[operation-plan] generic-adaptive selected; automation is plan-only."
    )
    return ProcessTurnResult(working, brief, overlay, None, working.operation_status)

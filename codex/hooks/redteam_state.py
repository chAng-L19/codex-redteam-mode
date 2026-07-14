from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path


VALID_MODES = {"normal", "redteam-light", "redteam-full"}
VALID_OPSEC = {"strict", "balanced"}
VALID_EVIDENCE = {"unknown", "partial", "confirmed"}
VALID_HEALTH = {"healthy", "strained", "degraded"}
VALID_DRIFT = {"low", "medium", "high"}
VALID_INTENTS = {"new", "continue", "revise", "verify", "summarize"}


def _safe_int(val, default: int = 0) -> int:
    """Convert value to int safely, returning default on failure."""
    try:
        return int(val or default)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    """Convert value to float safely, returning default on failure."""
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


@dataclass
class RedTeamState:
    mode: str = "normal"
    phase: str = "general"
    subphase: str = ""
    method: str = ""
    router: str = ""
    skill_pack: str = ""
    leaf_skill: str = ""
    evidence_level: str = "unknown"
    selected_path: str = ""
    review_required: bool = False
    opsec_level: str = "balanced"
    objective: str = ""
    intent_type: str = "continue"
    workflow_phase: str = "recon"
    loop_iteration: int = 0
    stagnation_count: int = 0
    drift_score: float = 0.0
    drift_level: str = "low"
    current_task_id: str = ""
    loop_health: str = "healthy"
    active_skill_count: int = 0
    pseudo_complete_count: int = 0
    last_reason_code: str = ""
    last_changed: str = ""
    session_id: str = ""
    evidence_artifacts: list = field(default_factory=list)
    pivot_count: int = 0
    # --- P3b: automation loop feedback fields ---
    recent_artifacts: list = field(default_factory=list)
    missing_capabilities: list = field(default_factory=list)
    selected_tools: list = field(default_factory=list)
    last_action: str = ""
    last_reason: str = ""

    def normalized(self) -> "RedTeamState":
        return RedTeamState(
            mode=self.mode if self.mode in VALID_MODES else "normal",
            phase=self.phase or "general",
            subphase=self.subphase or "",
            method=self.method or "",
            router=self.router or "",
            skill_pack=self.skill_pack or "",
            leaf_skill=self.leaf_skill or "",
            evidence_level=self.evidence_level if self.evidence_level in VALID_EVIDENCE else "unknown",
            selected_path=self.selected_path or "",
            review_required=bool(self.review_required),
            opsec_level=self.opsec_level if self.opsec_level in VALID_OPSEC else "balanced",
            objective=self.objective or "",
            intent_type=self.intent_type if self.intent_type in VALID_INTENTS else "continue",
            workflow_phase=self.workflow_phase or "recon",
            loop_iteration=max(0, _safe_int(self.loop_iteration)),
            stagnation_count=max(0, _safe_int(self.stagnation_count)),
            drift_score=max(0.0, _safe_float(self.drift_score)),
            drift_level=self.drift_level if self.drift_level in VALID_DRIFT else "low",
            current_task_id=self.current_task_id or "",
            loop_health=self.loop_health if self.loop_health in VALID_HEALTH else "healthy",
            active_skill_count=max(0, _safe_int(self.active_skill_count)),
            pseudo_complete_count=max(0, _safe_int(self.pseudo_complete_count)),
            last_reason_code=self.last_reason_code or "",
            last_changed=self.last_changed or now_iso(),
            session_id=self.session_id or "",
            evidence_artifacts=list(self.evidence_artifacts) if isinstance(self.evidence_artifacts, list) else [],
            pivot_count=max(0, _safe_int(self.pivot_count)),
            # P3b: automation loop feedback
            recent_artifacts=list(self.recent_artifacts) if isinstance(self.recent_artifacts, list) else [],
            missing_capabilities=list(self.missing_capabilities) if isinstance(self.missing_capabilities, list) else [],
            selected_tools=list(self.selected_tools) if isinstance(self.selected_tools, list) else [],
            last_action=self.last_action or "",
            last_reason=self.last_reason or "",
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_state(session_id: str | None = None) -> RedTeamState:
    return RedTeamState(last_changed=now_iso(), session_id=session_id or "")


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve(strict=False)
    return (Path.home() / ".codex").resolve(strict=False)


def state_root() -> Path:
    return codex_home() / "redteam-mode" / "state"


def state_dir() -> Path:
    return state_root() / "sessions"


def memory_dir() -> Path:
    return state_root() / "memory"


def _safe_session_key(session_id: str | None) -> str:
    raw = (session_id or "").strip()
    if not raw:
        raise ValueError("session_id is required for persistent red-team state")
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", raw)
    return safe[:120]


def state_path(session_id: str) -> Path:
    return state_dir() / f"{_safe_session_key(session_id)}.json"


def _coerce_state_payload(raw: dict) -> dict:
    valid_names = {item.name for item in fields(RedTeamState)}
    return {key: value for key, value in raw.items() if key in valid_names}


def load_state(session_id: str | None = None) -> RedTeamState:
    if not session_id or not session_id.strip():
        return default_state()
    path = state_path(session_id)
    if not path.exists():
        return default_state(session_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_state(session_id)
        state = RedTeamState(**_coerce_state_payload(raw)).normalized()
        if session_id and not state.session_id:
            state.session_id = session_id
        return state
    except Exception:
        return default_state(session_id)


def save_state(state: RedTeamState, session_id: str | None = None) -> None:
    state = state.normalized()
    effective_session_id = (session_id or state.session_id).strip()
    if not effective_session_id:
        return
    state.session_id = effective_session_id
    state.last_changed = now_iso()
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = state_path(effective_session_id)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)


def reset_state(session_id: str | None = None) -> RedTeamState:
    state = default_state(session_id)
    if session_id and session_id.strip():
        save_state(state, session_id=session_id)
    return state

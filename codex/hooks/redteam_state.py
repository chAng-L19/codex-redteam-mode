from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


VALID_MODES = {"normal", "redteam-light", "redteam-full"}
VALID_OPSEC = {"strict", "balanced"}
VALID_INTENTS = {"new", "continue", "revise", "verify", "summarize"}


@dataclass
class RedTeamState:
    mode: str = "normal"
    opsec_level: str = "balanced"
    objective: str = ""
    intent_type: str = "continue"
    last_changed: str = ""
    session_id: str = ""
    pending_action: dict = field(default_factory=dict)
    verified_artifacts: list = field(default_factory=list)
    workflow_terminal: bool = False
    active_model: str = ""
    active_prompt_profile: str = ""
    operation_run_id: str = ""
    operation_run_ids: list = field(default_factory=list)
    batch_session_id: str = ""
    workflow_id: str = ""
    operation_status: str = ""
    next_action_id: str = ""
    goal_terminal: bool = False
    goal_success: bool = False
    last_scene: str = ""
    last_action_kind: str = ""
    last_risk_level: str = ""
    last_context_bundle: list = field(default_factory=list)
    last_taxonomy: list = field(default_factory=list)

    def normalized(self) -> "RedTeamState":
        return RedTeamState(
            mode=self.mode if self.mode in VALID_MODES else "normal",
            opsec_level=self.opsec_level if self.opsec_level in VALID_OPSEC else "balanced",
            objective=self.objective or "",
            intent_type=self.intent_type if self.intent_type in VALID_INTENTS else "continue",
            last_changed=self.last_changed or now_iso(),
            session_id=self.session_id or "",
            pending_action=dict(self.pending_action) if isinstance(self.pending_action, dict) else {},
            verified_artifacts=list(self.verified_artifacts) if isinstance(self.verified_artifacts, list) else [],
            workflow_terminal=bool(self.workflow_terminal),
            active_model=self.active_model or "",
            active_prompt_profile=self.active_prompt_profile or "",
            operation_run_id=self.operation_run_id or "",
            operation_run_ids=list(self.operation_run_ids) if isinstance(self.operation_run_ids, list) else [],
            batch_session_id=self.batch_session_id or "",
            workflow_id=self.workflow_id or "",
            operation_status=self.operation_status or "",
            next_action_id=self.next_action_id or "",
            goal_terminal=bool(self.goal_terminal),
            goal_success=bool(self.goal_success),
            last_scene=self.last_scene or "",
            last_action_kind=self.last_action_kind or "",
            last_risk_level=self.last_risk_level or "",
            last_context_bundle=list(self.last_context_bundle) if isinstance(self.last_context_bundle, list) else [],
            last_taxonomy=list(self.last_taxonomy) if isinstance(self.last_taxonomy, list) else [],
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


@contextmanager
def session_state_lock(session_id: str, *, timeout_seconds: float = 10.0) -> Iterator[None]:
    target = state_path(session_id)
    directory = target.parent
    directory.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        directory.chmod(0o700)
    lock_path = target.with_name(f"{target.name}.lock")
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30.0
            except FileNotFoundError:
                continue
            if stale:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"session_state_lock_timeout:{session_id}")
            time.sleep(0.01)
            continue
        try:
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        finally:
            os.close(descriptor)
        break
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


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
    if os.name != "nt":
        directory.chmod(0o700)
    target = state_path(effective_session_id)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    if os.name != "nt":
        tmp.chmod(0o600)
    tmp.replace(target)
    if os.name != "nt":
        target.chmod(0o600)


def reset_state(session_id: str | None = None) -> RedTeamState:
    state = default_state(session_id)
    if session_id and session_id.strip():
        save_state(state, session_id=session_id)
    return state

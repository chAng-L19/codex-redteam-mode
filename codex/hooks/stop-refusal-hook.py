#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CODEX_DIR = HOOKS_DIR.parent
for candidate in (HOOKS_DIR, CODEX_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from core import extract_session_id, load_runtime_state, save_runtime_state
from core.prompt_parser import decode_stdin
from core.refusal_backstop import message_has_refusal


def main() -> None:
    raw = decode_stdin(sys.stdin.buffer.read())
    if not raw.strip():
        print("{}")
        return
    try:
        payload = json.loads(raw)
    except Exception:
        print("{}")
        return
    if not isinstance(payload, dict):
        print("{}")
        return

    session_id = extract_session_id(payload)
    turn_id = payload.get("turn_id")
    stop_hook_active = payload.get("stop_hook_active")
    last_message = payload.get("last_assistant_message")
    if (
        not session_id
        or not isinstance(turn_id, str)
        or not turn_id.strip()
        or not isinstance(stop_hook_active, bool)
        or stop_hook_active
        or not isinstance(last_message, str)
    ):
        print("{}")
        return

    state = load_runtime_state(session_id=session_id)
    normalized_turn_id = turn_id.strip()
    if (
        state.mode != "normal"
        and state.last_refusal_turn_id != normalized_turn_id
        and message_has_refusal(last_message)
    ):
        state = replace(
            state,
            pending_refusal_overlay=True,
            last_refusal_turn_id=normalized_turn_id,
        )
        save_runtime_state(state, session_id=session_id)

    print("{}")


if __name__ == "__main__":
    main()

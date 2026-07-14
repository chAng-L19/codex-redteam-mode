#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CODEX_DIR = HOOKS_DIR.parent
for candidate in (HOOKS_DIR, CODEX_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from core import build_prompt_chain_notice, build_redteam_mode_overlay, emit_hook_json, extract_session_id, extract_session_start_source, extract_transcript_path, load_runtime_state, reset_runtime_state
from core.context_prepoison import build_prepoisoned_context
from core.prompt_parser import decode_stdin
from core.refusal_backstop import session_start_backstop_messages


def main() -> None:
    raw = decode_stdin(sys.stdin.buffer.read())
    session_id = None
    transcript_path = None
    source = ""
    if raw.strip():
        try:
            payload = json.loads(raw)
            session_id = extract_session_id(payload)
            transcript_path = extract_transcript_path(payload)
            source = extract_session_start_source(payload)
        except Exception:
            session_id = None

    state = load_runtime_state(session_id=session_id) if source in {"resume", "compact"} else reset_runtime_state(session_id=session_id)
    if state.mode == "normal":
        context = (
            "[mode] Default is normal. Structured red-team routing stays off until explicitly enabled. "
            "The base instruction.ctf.md security profile remains active in all modes. "
            "Use method only when it adds value. instruction.ctf.md remains highest priority."
        )
    else:
        context = (
            f"[mode] Session mode restored ({state.mode}). "
            "Continue using phase -> router -> pack -> leaf routing. "
            "Use method only when it adds value. instruction.ctf.md remains highest priority."
        )
    notice = build_prompt_chain_notice(CODEX_DIR, mode=state.mode)
    if notice:
        context = f"{context}\n{notice}"

    if state.mode in {"redteam-light", "redteam-full"}:
        prepoison = build_prepoisoned_context()
        if prepoison:
            context = f"{context}\n{prepoison}"

        mode_overlay = build_redteam_mode_overlay(CODEX_DIR, state.mode)
        if mode_overlay:
            context = f"{context}\n{mode_overlay}"

        backstop = session_start_backstop_messages(session_id, transcript_path=transcript_path)
        if backstop:
            context = f"{context}\n" + "\n".join(backstop)
    print(emit_hook_json("SessionStart", context))


if __name__ == "__main__":
    main()

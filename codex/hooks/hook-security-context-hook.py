#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CODEX_DIR = HOOKS_DIR.parent
for candidate in (HOOKS_DIR, CODEX_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from core import build_redteam_mode_overlay, emit_hook_json, extract_prompt, extract_session_id, is_pinned_model_compatible, load_runtime_state, parse_mode_command, parse_opsec_command, resolve_model_prompt_profile, save_runtime_state
from core.controller import process_turn
from core.prompt_parser import decode_stdin
from core.refusal_backstop import build_recent_refusal_overlay
from redteam_state import default_state


def main() -> None:
    raw = decode_stdin(sys.stdin.buffer.read())
    if not raw.strip():
        return
    try:
        payload = json.loads(raw)
    except Exception:
        return
    if not isinstance(payload, dict):
        return

    prompt = extract_prompt(payload)
    if not prompt.strip():
        return

    session_id = extract_session_id(payload)
    if not session_id:
        return
    state = load_runtime_state(session_id=session_id)
    profile = resolve_model_prompt_profile(CODEX_DIR, payload=payload)
    catalog = "single-profile" if os.environ.get("CODEX_REDTEAM_PROFILE_MODE", "").casefold() == "single" else "static"
    if catalog == "single-profile":
        pinned_model = os.environ.get("CODEX_REDTEAM_PINNED_MODEL", "").strip()
        pinned_profile = os.environ.get("CODEX_REDTEAM_PINNED_PROFILE", "").strip()
        if not is_pinned_model_compatible(profile.model, pinned_model, pinned_profile):
            reason = (
                f"当前 Codex 进程锁定模型族为 {pinned_profile or 'unknown'}，但本轮模型为 {profile.model}。"
                "请使用 /model 切回兼容模型，或退出后使用新的 --model 参数重新启动。\n"
                f"The locked model family for this Codex process is {pinned_profile or 'unknown'}, but the current "
                f"model is {profile.model}. Switch back with /model or restart with a new --model value."
            )
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=True))
            return
    selector = profile.render(scope="current-turn", catalog=catalog)
    state.active_model = profile.model
    state.active_prompt_profile = profile.profile

    mode = parse_mode_command(prompt)
    if mode is not None:
        if mode == "normal":
            state = replace(
                default_state(session_id),
                active_model=profile.model,
                active_prompt_profile=profile.profile,
            )
            save_runtime_state(state, session_id=session_id)
            print(
                emit_hook_json(
                    "UserPromptSubmit",
                    "[mode] Structured red-team routing disabled for future turns. "
                    "No new phase/router/pack/leaf context will be injected. "
                    "The base instruction.ctf.md profile and previous task context remain active. "
                    "The session state file remains stored with mode reset to normal. "
                    "Use /clear or start a new task to remove prior per-session context.\n"
                    f"{selector}",
                )
            )
        else:
            state = replace(
                default_state(session_id),
                mode=mode,
                opsec_level=state.opsec_level,
                active_model=profile.model,
                active_prompt_profile=profile.profile,
            )
            save_runtime_state(state, session_id=session_id)
            context = (
                f"[mode] Red-team mode enabled ({mode}). Future prompts will use "
                "phase -> router -> pack -> leaf routing until you explicitly disable it."
            )
            mode_overlay = build_redteam_mode_overlay(CODEX_DIR, mode)
            if mode_overlay:
                context = f"{context}\n{mode_overlay}"
            context = f"{context}\n{selector}"
            print(
                emit_hook_json(
                    "UserPromptSubmit",
                    context,
                    inject_prepoison=True,
                )
            )
        return

    opsec = parse_opsec_command(prompt)
    if opsec is not None:
        state = replace(state, opsec_level=opsec)
        save_runtime_state(state, session_id=session_id)
        print(emit_hook_json("UserPromptSubmit", f"[mode] OPSEC level updated to {opsec}.\n{selector}"))
        return

    if state.mode == "normal":
        save_runtime_state(state, session_id=session_id)
        print(emit_hook_json("UserPromptSubmit", selector))
        return

    result = process_turn(
        prompt=prompt,
        state=state,
        codex_dir=CODEX_DIR,
        assistant_summary="",
    )
    next_state = result.state
    next_state.active_model = profile.model
    next_state.active_prompt_profile = profile.profile
    context = f"{result.brief}\n{selector}"
    if state.pending_refusal_overlay:
        context = f"{context}\n{build_recent_refusal_overlay()}"
        next_state = replace(next_state, pending_refusal_overlay=False)
    if result.overlay:
        context = f"{context}\n{result.overlay}"
    save_runtime_state(next_state, session_id=session_id)
    print(emit_hook_json("UserPromptSubmit", context, inject_role_overlay=True, role_phase=next_state.phase))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import sys
from dataclasses import replace
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
CODEX_DIR = HOOKS_DIR.parent
for candidate in (HOOKS_DIR, CODEX_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from core import build_prompt_overlay, build_route_envelope, detect_phase, emit_hook_json, extract_prompt, extract_session_id, load_runtime_state, parse_mode_command, parse_opsec_command, save_runtime_state
from core.prompt_parser import decode_stdin, load_payload
from router import select_leaf_skill, select_method, select_router, select_skill_pack, select_subphase

STRONG_EVIDENCE_TOKENS = ("burp raw", "raw request", "raw response", "pcap", "wireshark", "tcpdump", "nmap", "fscan", "traceback", "stack trace", "log excerpt", "controller", "middleware", "source code", "sample", "payload bytes")
PARTIAL_EVIDENCE_TOKENS = ("request", "response", "review", "source", "code", "shell", "reverse", "audit", "token", "session", "traffic")

def infer_evidence_level(prompt: str) -> str:
    lowered = prompt.casefold()
    if any(token in lowered for token in STRONG_EVIDENCE_TOKENS): return "confirmed"
    if any(token in lowered for token in PARTIAL_EVIDENCE_TOKENS): return "partial"
    return "unknown"

def main() -> None:
    raw = decode_stdin(sys.stdin.buffer.read())
    if not raw.strip(): return
    try: payload = load_payload(raw)
    except Exception: return
    prompt = extract_prompt(payload)
    if not prompt.strip(): return
    session_id = extract_session_id(payload)
    state = load_runtime_state(session_id=session_id)
    mode = parse_mode_command(prompt)
    if mode is not None:
        state = replace(state, mode=mode, phase="general", subphase="", method="", router="", skill_pack="", leaf_skill="", evidence_level="unknown", selected_path="", review_required=False)
        save_runtime_state(state, session_id=session_id)
        if mode == "normal":
            print(emit_hook_json("UserPromptSubmit", "[mode] Red-team mode disabled. Return to normal mode; do not inject offensive doctrine unless you explicitly enable it again."))
        else:
            print(emit_hook_json("UserPromptSubmit", f"[mode] Red-team mode enabled ({mode}). Future prompts will use phase -> router -> pack -> leaf routing until you explicitly disable it."))
        return
    opsec = parse_opsec_command(prompt)
    if opsec is not None:
        state = replace(state, opsec_level=opsec)
        save_runtime_state(state, session_id=session_id)
        print(emit_hook_json("UserPromptSubmit", f"[mode] OPSEC level updated to {opsec}."))
        return
    if state.mode == "normal": return
    phase = detect_phase(prompt)
    subphase = select_subphase(prompt, phase)
    method = select_method(prompt, phase, state.mode)
    router = select_router(prompt, phase)
    skill_pack = select_skill_pack(phase, router)
    leaf_skill = select_leaf_skill(prompt, phase, router)
    evidence_level = infer_evidence_level(prompt)
    selected_path = leaf_skill if leaf_skill and leaf_skill != "hack" else router
    review_required = state.mode == "redteam-full" or phase in {"code-audit", "reverse", "payload", "evasion"}
    state = replace(state, phase=phase, subphase=subphase, method=method, router=router, skill_pack=skill_pack, leaf_skill=leaf_skill, evidence_level=evidence_level, selected_path=selected_path, review_required=review_required)
    save_runtime_state(state, session_id=session_id)
    context = build_route_envelope(state)
    overlay = build_prompt_overlay(CODEX_DIR, phase)
    if overlay: context = f"{context}\n{overlay}"
    print(emit_hook_json("UserPromptSubmit", context))

if __name__ == "__main__":
    main()

from __future__ import annotations

import re
from typing import Optional

ENABLE_PATTERNS = [
    (r"/redteam\s+full\b", "redteam-full"),
    (r"/redteam\s+light\b", "redteam-light"),
    (r"/redteam\s+on\b", "redteam-light"),
    ("进入红队模式", "redteam-light"),
    ("开启红队模式", "redteam-light"),
    (r"enable\s+red\s*team\s*mode", "redteam-light"),
]

DISABLE_PATTERNS = [
    "退出红队模式",
    "关闭红队模式",
    r"/redteam\s+off\b",
    r"disable\s+red\s*team\s*mode",
]

OPSEC_PATTERNS = [
    (r"/opsec\s+strict\b", "strict"),
    (r"/opsec\s+balanced\b", "balanced"),
]

SESSION_START_SOURCES = {"startup", "resume", "clear", "compact"}


def decode_stdin(data: bytes) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


def extract_prompt(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get("prompt")
    return value if isinstance(value, str) else ""


def extract_session_id(payload: object) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    value = payload.get("session_id")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def extract_transcript_path(payload: object) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    value = payload.get("transcript_path")
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def extract_session_start_source(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get("source")
    if not isinstance(value, str):
        return ""
    source = value.strip().casefold()
    return source if source in SESSION_START_SOURCES else ""


def parse_mode_command(prompt: str) -> Optional[str]:
    candidate = prompt.strip()
    for pat, mode in ENABLE_PATTERNS:
        if re.fullmatch(pat, candidate, re.I):
            return mode
    for pat in DISABLE_PATTERNS:
        if re.fullmatch(pat, candidate, re.I):
            return "normal"
    return None


def parse_opsec_command(prompt: str) -> Optional[str]:
    candidate = prompt.strip()
    for pat, level in OPSEC_PATTERNS:
        if re.fullmatch(pat, candidate, re.I):
            return level
    return None

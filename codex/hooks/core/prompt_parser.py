from __future__ import annotations

import json
import re
from typing import Any, Optional

ENABLE_PATTERNS = [
    (r"/redteam\s+full\b", "redteam-full"),
    (r"/redteam\s+light\b", "redteam-light"),
    (r"进入红队模式", "redteam-light"),
    (r"开启红队模式", "redteam-light"),
    (r"/redteam\s+on\b", "redteam-light"),
    (r"enable\s+red\s*team\s*mode", "redteam-light"),
]

DISABLE_PATTERNS = [
    r"退出红队模式",
    r"关闭红队模式",
    r"/redteam\s+off\b",
    r"disable\s+red\s*team\s*mode",
]

OPSEC_PATTERNS = [
    (r"/opsec\s+strict\b", "strict"),
    (r"/opsec\s+balanced\b", "balanced"),
]


def decode_stdin(data: bytes) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


def load_payload(raw: str) -> Any:
    return json.loads(raw)


def extract_prompt(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("prompt", "input", "text", "message", "user_prompt"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    messages = payload.get("messages")
    if isinstance(messages, list):
        parts: list[str] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        parts.append(block["text"])
        return "\n".join(parts)
    return ""


SESSION_ID_KEYS = (
    "session_id","sessionId","thread_id","threadId","conversation_id","conversationId","chat_id","chatId","id",
)


def extract_session_id(payload: Any) -> Optional[str]:
    if isinstance(payload, str):
        return None
    if isinstance(payload, dict):
        for key in SESSION_ID_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("context", "session", "thread", "conversation", "metadata", "_meta", "meta"):
            nested = payload.get(key)
            found = extract_session_id(nested)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = extract_session_id(item)
            if found:
                return found
    return None


def parse_mode_command(prompt: str) -> Optional[str]:
    for pat, mode in ENABLE_PATTERNS:
        if re.search(pat, prompt, re.I):
            return mode
    for pat in DISABLE_PATTERNS:
        if re.search(pat, prompt, re.I):
            return "normal"
    return None


def parse_opsec_command(prompt: str) -> Optional[str]:
    for pat, level in OPSEC_PATTERNS:
        if re.search(pat, prompt, re.I):
            return level
    return None

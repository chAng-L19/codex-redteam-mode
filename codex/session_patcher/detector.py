# -*- coding: utf-8 -*-
"""Refusal detector for Codex CLI session JSONL files."""

from typing import Dict, List, Optional


class RefusalDetector:
    """Two-tier refusal detection: strong phrases (full-text) + weak keywords (head-150 chars)."""

    STRONG_REFUSAL_PHRASES = [
        # Chinese — high confidence
        "我无法协助", "我无法帮助", "我不能协助", "我不能帮助",
        "我不能做", "我无法做", "我不会帮", "我无法提供",
        "违反了我的", "违反我的", "这违反",
        "我拒绝", "我必须拒绝",
        "无法协助你", "无法帮你",
        "我不能为你", "我无法为你",
        # English — high confidence
        "i cannot assist", "i can't assist", "i'm unable to assist",
        "i cannot help", "i can't help", "i'm unable to help",
        "i must decline", "i must refuse",
        "against my guidelines", "against my policy",
        "violates my", "i won't help", "i won't assist",
        "as an ai", "as a language model",
        "i apologize, but i", "i'm sorry, but i can't",
        "not able to provide", "not able to assist",
        "cannot provide", "cannot comply",
    ]

    WEAK_REFUSAL_KEYWORDS = [
        # Chinese — only at message start
        "抱歉", "很抱歉", "对不起", "不好意思",
        "我无法", "我不能", "不允许", "禁止",
        "不能帮你", "不能协助", "无法帮你",
        "不会帮你", "不会帮助",
        # English — only at message start
        "sorry", "apologize", "i cannot", "i can't",
        "i'm unable", "unable to", "not permitted", "not allowed",
        "refuse to",
    ]

    def __init__(self, custom_keywords: Optional[Dict[str, List[str]]] = None):
        self.custom_keywords: Dict[str, List[str]] = {}
        if custom_keywords:
            for lang, words in custom_keywords.items():
                self.custom_keywords[lang] = list(words)

    def detect(self, content: str) -> bool:
        """Detect whether content contains a refusal response.

        Strategy:
        1. Strong phrases — match anywhere in text (low false positive rate)
        2. Weak keywords — only match in first 150 characters
        3. Custom keywords — match anywhere (full-text)
        """
        if not content:
            return False

        content_lower = content.lower()

        for phrase in self.STRONG_REFUSAL_PHRASES:
            if phrase in content_lower:
                return True

        head = content_lower[:150]
        for keyword in self.WEAK_REFUSAL_KEYWORDS:
            if keyword in head:
                return True

        for lang_keywords in self.custom_keywords.values():
            for keyword in lang_keywords:
                if keyword.lower() in content_lower:
                    return True

        return False

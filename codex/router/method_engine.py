from __future__ import annotations
import re
from .mappings import PHASE_DEFAULT_METHOD, PHASE_ESCALATION_METHOD
METHOD_HINTS = [
    ("workflows", [r"\bworkflow\b", r"\bplaybook\b", r"\bchain\b", r"工作流", r"流程", r"多阶段"]),
    ("overall-planning", [r"\bplan\b", r"\broadmap\b", r"路线图", r"整体规划", r"全局规划"]),
    ("concentrate-forces", [r"\bpriorit", r"\bwhich path\b", r"优先", r"先打哪条", r"主攻方向"]),
    ("contradiction-analysis", [r"\btrade[- ]?off\b", r"\bcompare\b", r"权衡", r"对比", r"矛盾"]),
    ("practice-cognition", [r"\bpoc\b", r"\bscaffold\b", r"脚手架", r"验证骨架", r"构建"]),
    ("investigation-first", [r"\banalyze\b", r"\btrace\b", r"\breconstruct\b", r"分析", r"追踪", r"梳理"]),
    ("criticism-self-criticism", [r"\bself[- ]?review\b", r"\bpostmortem\b", r"复盘", r"自审", r"批评"]),
]
def select_method(prompt: str, phase: str, mode: str) -> str:
    for method, patterns in METHOD_HINTS:
        if any(re.search(pat, prompt, re.I) for pat in patterns):
            return method
    if mode == "redteam-full":
        return PHASE_ESCALATION_METHOD.get(phase, PHASE_DEFAULT_METHOD.get(phase, "overall-planning"))
    return ""

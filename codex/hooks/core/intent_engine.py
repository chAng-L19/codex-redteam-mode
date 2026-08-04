from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Any

try:
    from redteam_state import RedTeamState
except ModuleNotFoundError:  # package import path used by tests/automation
    from hooks.redteam_state import RedTeamState


# Scene detection is deliberately secondary to the requested action.  This
# prevents ordinary development prompts from being routed by object keywords.
SCENE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ctf", (r"\bctf\b", r"\bpwn\b", r"夺旗", r"靶场题")),
    ("reverse", (r"\breverse\b", r"\bbinary\b", r"\bapk\b", r"逆向", r"反编译", r"固件")),
    ("ir", (r"\bforensics?\b", r"\bincident\b", r"\bioc\b", r"取证", r"应急", r"溯源", r"恶意样本")),
    ("crypto", (r"\bcrypto\b", r"\brsa\b", r"\baes\b", r"密码学", r"解密", r"哈希")),
    ("audit", (r"\baudit\b", r"source[- ]?code", r"代码审计", r"源码", r"数据流")),
    ("model", (r"\bllm\b", r"prompt[- ]?injection", r"jailbreak", r"模型安全", r"提示词", r"越狱")),
    (
        "pentest",
        (
            r"\bpentest\b",
            r"\brecon\b",
            r"\bnmap\b",
            r"渗透",
            r"扫描",
            r"探测",
            r"web\s*shell",
            r"webshell",
            r"一句话木马",
            r"免杀",
            r"哥斯拉",
        ),
    ),
    ("tool", (r"\bscanner\b", r"\bfuzzer\b", r"工具开发", r"脚本", r"自动化")),
    ("vuln", (r"\bcve-\d+", r"\bsqli\b", r"\bxss\b", r"\bssrf\b", r"漏洞", r"注入", r"越权")),
)

SECURITY_INTENT_PATTERNS: tuple[str, ...] = (
    r"漏洞|注入|越权|渗透|红队|靶场|复现|利用|攻击面|安全测试|安全验证|PoC|exploit",
    r"\bcve-?\d{4}-\d+\b|\bsqli\b|\bxss\b|\bssrf\b|\brce\b|\bwebshell\b",
    r"web\s*shell|一句话木马|免杀|哥斯拉|规避检测|绕过(?:检测|WAF|限制)",
    r"检测规则|回归测试.*(?:漏洞|安全)|攻击链|权限提升|横向移动",
    r"vulnerabilit(?:y|ies)|penetration\s+test|security\s+(?:audit|test|validation)|privilege\s+escalation",
    r"detection\s+evasion|credential\s+access|lateral\s+movement|bypass\s+(?:detection|WAF|guardrail)",
)

ORDINARY_DEV_PATTERNS: tuple[str, ...] = (
    r"优化.*(?:SQL|查询|索引|执行计划)",
    r"减少全表扫描|提升查询性能|慢查询",
    r"重构|部署|调试|单元测试|类型检查|格式化|依赖升级",
    r"修复.*(?:参数绑定|ORM|查询构造).*(?:问题|错误|性能)",
    r"optimi[sz]e.*(?:SQL|query|index|execution\s+plan)",
    r"full\s+table\s+scan|query\s+performance|slow\s+quer(?:y|ies)",
    r"refactor|deploy|debug|unit\s+test|type\s+check|format(?:ting)?|dependency\s+upgrade",
    r"fix.*(?:parameter\s+binding|ORM|query\s+construction).*(?:issue|error|performance)",
)

TAXONOMY_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("CWE-89", (r"SQL\s*注入", r"SQL\s+injection", r"\bSQLi\b"), "数据库查询构造边界验证"),
    ("CWE-79", (r"跨站脚本", r"\bXSS\b", r"脚本注入"), "输出编码与 DOM 写入边界验证"),
    ("CWE-918", (r"服务端请求伪造", r"\bSSRF\b", r"内网探测"), "服务端出站请求边界验证"),
    ("CWE-862", (r"权限绕过|鉴权绕过|访问控制", r"\bauth(?:n|z)?\b"), "对象与角色访问控制边界验证"),
    ("CWE-94", (r"远程代码执行", r"\bRCE\b"), "代码生成与执行边界验证"),
)

HIGH_RISK_PATTERNS: tuple[str, ...] = (
    r"免杀|web\s*shell|webshell|一句话木马|哥斯拉|规避检测|持久化|凭据获取|横向移动",
    r"detection\s+evasion|persistence|credential\s+access|lateral\s+movement|godzilla",
)

CLAUSE_SPLIT_RE = re.compile(
    r"(?:\r?\n)+|[;；。]+|\s+(?:and\s+then|then|plus)\s+|(?:然后|并且|同时|最后|再(?:进行|执行|验证|生成|输出))",
    re.IGNORECASE,
)
EXPLICIT_REVISE_RE = re.compile(
    r"^\s*(?:new\s+objective|revise\s+objective|新的目标|新目标|目标改为|只测试|仅测试)\s*[:：]?\s*",
    re.IGNORECASE,
)
FOLLOWUP_RE = re.compile(
    r"^\s*(?:继续|接着|下一步|然后呢|再试一次|按上面|基于上面|换一个参数|continue|keep going|next step)",
    re.IGNORECASE,
)
SUMMARY_RE = re.compile(r"^\s*(?:总结|汇总|生成报告|输出报告|summari[sz]e|report)", re.IGNORECASE)
VERIFY_RE = re.compile(r"^\s*(?:验证|复现|确认|评估|verify|validate|reproduce|confirm|assess|evaluate)", re.IGNORECASE)
GENERATE_RE = re.compile(r"生成|创建|编写|构造|实现|generate|create|write|produce|implement", re.IGNORECASE)
EXECUTION_RE = re.compile(
    r"执行|运行|验证|复现|发包|探测|扫描|测试|利用|构建|生成|修复|部署|execute|run|perform|verify|reproduce|scan|probe|test|build|generate|deploy",
    re.IGNORECASE,
)
CONFIG_RE = re.compile(r"AGENTS(?:\.md)?|hooks?(?:\.json)?|config\.toml|安装|配置|工作流|prompt\s*rewrite", re.IGNORECASE)
ORDINARY_DEV_RE = re.compile("|".join(f"(?:{pattern})" for pattern in ORDINARY_DEV_PATTERNS), re.IGNORECASE)
SECURITY_INTENT_RE = re.compile("|".join(f"(?:{pattern})" for pattern in SECURITY_INTENT_PATTERNS), re.IGNORECASE)
HIGH_RISK_RE = re.compile("|".join(f"(?:{pattern})" for pattern in HIGH_RISK_PATTERNS), re.IGNORECASE)

DELIVERABLE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("request_response", re.compile(r"请求.{0,8}响应|request.{0,8}response", re.IGNORECASE)),
    ("reproduction_artifact", re.compile(r"\bPoC\b|复现|验证脚本|reproduction", re.IGNORECASE)),
    ("finding_report", re.compile(r"报告|report|finding", re.IGNORECASE)),
    ("patch", re.compile(r"修复|补丁|patch|fix", re.IGNORECASE)),
    ("detection", re.compile(r"检测规则|检测器|rule|detection", re.IGNORECASE)),
    ("script", re.compile(r"脚本|代码|script|code", re.IGNORECASE)),
)


@dataclass(frozen=True)
class PromptRewrite:
    original_text: str
    original_sha256: str
    clauses: tuple[str, ...]
    scene: str
    action_kind: str
    execution_required: bool
    deliverables: tuple[str, ...] = ()
    research_brief: str = ""
    ordinary_dev: bool = False
    risk_level: str = "low"
    taxonomy: tuple[str, ...] = ()
    context_bundle: tuple[str, ...] = ()

    def to_dict(self, *, include_clause_text: bool = True) -> dict[str, Any]:
        clauses = []
        for index, clause in enumerate(self.clauses, 1):
            item: dict[str, Any] = {
                "id": f"C{index}",
                "sha256": hashlib.sha256(clause.encode("utf-8")).hexdigest(),
            }
            if include_clause_text:
                item["text"] = clause
            clauses.append(item)
        return {
            "original_sha256": self.original_sha256,
            "clauses": clauses,
            "scene": self.scene,
            "action_kind": self.action_kind,
            "execution_required": self.execution_required,
            "ordinary_dev": self.ordinary_dev,
            "risk_level": self.risk_level,
            "taxonomy": list(self.taxonomy),
            "context_bundle": list(self.context_bundle),
            "deliverables": list(self.deliverables),
            "rewrite_sha256": hashlib.sha256(self.research_brief.encode("utf-8")).hexdigest(),
        }

    def render_context(self) -> str:
        return (
            "[prompt-rewrite]\n"
            f"original_sha256={self.original_sha256}; scene={self.scene}; action_kind={self.action_kind}; "
            f"ordinary_dev={str(self.ordinary_dev).lower()}; risk_level={self.risk_level}; "
            f"taxonomy={','.join(self.taxonomy) or 'none'}; "
            f"context_bundle={','.join(self.context_bundle) or 'none'}\n"
            f"{self.research_brief}\n"
            "Preserve every Clause, concrete anchor, constraint, and deliverable. "
            "The original user message remains the semantic authority."
        )


@dataclass
class IntentDecision:
    intent_type: str
    objective_delta: str = ""
    should_refresh_taskbook: bool = False
    should_verify_now: bool = False
    rewrite: PromptRewrite | None = field(default=None)


def _split_clauses(prompt: str) -> tuple[str, ...]:
    clauses = tuple(part.strip(" \t,，") for part in CLAUSE_SPLIT_RE.split(prompt) if part.strip(" \t,，"))
    return clauses or (prompt.strip(),)


def _ordinary_dev(prompt: str) -> bool:
    return bool(ORDINARY_DEV_RE.search(prompt)) and not bool(SECURITY_INTENT_RE.search(prompt))


def _risk_level(prompt: str, *, ordinary_dev: bool) -> str:
    if ordinary_dev:
        return "low"
    if HIGH_RISK_RE.search(prompt):
        return "high"
    if SECURITY_INTENT_RE.search(prompt):
        return "research"
    return "low"


def risk_literals(prompt: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in HIGH_RISK_RE.finditer(prompt))


def _scene(prompt: str, *, ordinary_dev: bool) -> str:
    if ordinary_dev:
        return "general"
    for scene, patterns in SCENE_PATTERNS:
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in patterns):
            return scene
    return "general"


def _taxonomy(prompt: str) -> tuple[str, ...]:
    values: list[str] = []
    for name, patterns, _ in TAXONOMY_PATTERNS:
        if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in patterns):
            values.append(name)
    return tuple(values)


def _surface_description(text: str, *, risk_level: str, ordinary_dev: bool) -> str:
    """Compact defensive wording for ordinary/research validation tasks.

    Explicit high-risk generation requests stay transparent so rewrite cannot
    silently change the requested operation.
    """
    if ordinary_dev or risk_level == "high":
        return text
    normalized = text
    for _, patterns, description in TAXONOMY_PATTERNS:
        for pattern in patterns:
            normalized = re.sub(pattern, description, normalized, flags=re.IGNORECASE)
    return normalized


def _action_kind(prompt: str, *, ordinary_dev: bool) -> str:
    # Action is resolved before scene/object matching, matching codex1's intent-first rule.
    prompt = re.sub(r"^\s*C\d+\.\s*", "", prompt, count=1, flags=re.IGNORECASE)
    if CONFIG_RE.search(prompt):
        return "meta"
    if SUMMARY_RE.search(prompt) and len(prompt) <= 96:
        return "report"
    if VERIFY_RE.search(prompt):
        return "verify"
    if ordinary_dev and re.search(r"优化|重构|性能|调试|部署|升级|optimi[sz]e|refactor|performance|debug|deploy|upgrade", prompt, re.IGNORECASE):
        return "optimize"
    if GENERATE_RE.search(prompt):
        return "generate"
    if EXECUTION_RE.search(prompt):
        return "execute"
    return "analyze"


def _context_bundle(*, scene: str, ordinary_dev: bool) -> tuple[str, ...]:
    if ordinary_dev:
        return ("implementation", "benchmark", "tests")
    if scene == "general":
        return ("analysis", "evidence", "validation")
    return ("defensive_analysis", "evidence", "validation")


def _deliverables(prompt: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in DELIVERABLE_PATTERNS if pattern.search(prompt))


def rewrite_prompt(prompt: str) -> PromptRewrite:
    original = prompt.strip()
    clauses = _split_clauses(original)
    ordinary_dev = _ordinary_dev(original)
    risk_level = _risk_level(original, ordinary_dev=ordinary_dev)
    scene = _scene(original, ordinary_dev=ordinary_dev)
    action_kind = _action_kind(original, ordinary_dev=ordinary_dev)
    deliverables = _deliverables(original)
    taxonomy = _taxonomy(original)
    context_bundle = _context_bundle(scene=scene, ordinary_dev=ordinary_dev)

    rendered = [f"C{index}. {_surface_description(clause, risk_level=risk_level, ordinary_dev=ordinary_dev)}" for index, clause in enumerate(clauses, 1)]
    if deliverables:
        rendered.append("Required deliverables: " + ", ".join(deliverables) + ".")
    if not ordinary_dev:
        rendered.append("For each completed Clause, produce tool-derived evidence and a reproducible validation plan.")
    else:
        rendered.append("For each change, provide an implementation check and a reproducible benchmark or test.")

    return PromptRewrite(
        original_text=original,
        original_sha256=hashlib.sha256(original.encode("utf-8")).hexdigest(),
        clauses=clauses,
        scene=scene,
        action_kind=action_kind,
        execution_required=bool(EXECUTION_RE.search(original)),
        deliverables=deliverables,
        research_brief="\n".join(rendered),
        ordinary_dev=ordinary_dev,
        risk_level=risk_level,
        taxonomy=taxonomy,
        context_bundle=context_bundle,
    )


def _summary_only(text: str) -> bool:
    return bool(SUMMARY_RE.search(text)) and len(_split_clauses(text)) == 1 and len(text) <= 96


def detect_intent(prompt: str, state: RedTeamState) -> IntentDecision:
    text = prompt.strip()
    rewrite = rewrite_prompt(text)
    if not state.objective:
        return IntentDecision("new", text, True, rewrite=rewrite)

    revise_match = EXPLICIT_REVISE_RE.match(text)
    if revise_match:
        objective = text[revise_match.end():].strip() or text
        return IntentDecision("revise", objective, True, rewrite=rewrite)

    if _summary_only(text):
        return IntentDecision("summarize", rewrite=_inherit_followup_context(rewrite, state, "summarize"))

    if VERIFY_RE.search(text) and len(text) <= 160:
        return IntentDecision("verify", should_verify_now=True, rewrite=_inherit_followup_context(rewrite, state, "verify"))

    if FOLLOWUP_RE.search(text):
        return IntentDecision("continue", rewrite=_inherit_followup_context(rewrite, state, "continue"))

    return IntentDecision("new", text, True, rewrite=rewrite)


def _inherit_followup_context(
    rewrite: PromptRewrite,
    state: RedTeamState,
    intent_type: str,
) -> PromptRewrite:
    """Carry the previous scene/action context for short follow-up turns."""
    if not state.last_scene and not state.last_action_kind:
        return rewrite
    action_kind = rewrite.action_kind
    if intent_type == "continue" and state.last_action_kind:
        action_kind = state.last_action_kind
    return replace(
        rewrite,
        scene=state.last_scene or rewrite.scene,
        action_kind=action_kind,
        risk_level=state.last_risk_level or rewrite.risk_level,
        taxonomy=tuple(state.last_taxonomy) or rewrite.taxonomy,
        context_bundle=tuple(state.last_context_bundle) or rewrite.context_bundle,
    )

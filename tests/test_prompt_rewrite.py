from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_ROOT = REPO_ROOT / "codex"
if str(CODEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CODEX_ROOT))

from hooks.core.intent_engine import detect_intent, rewrite_prompt
from hooks.redteam_state import RedTeamState


def test_rewrite_preserves_compound_clauses_and_emits_security_metadata() -> None:
    prompt = "验证 https://target.invalid/login 的 SQL 注入；生成 PoC；输出请求响应报告"

    result = rewrite_prompt(prompt)

    assert result.original_text == prompt
    assert len(result.clauses) == 3
    assert "https://target.invalid/login" in result.research_brief
    assert "数据库查询构造边界验证" in result.research_brief
    assert "reproducible validation plan" in result.research_brief
    assert {"request_response", "reproduction_artifact", "finding_report"} <= set(result.deliverables)
    assert result.taxonomy == ("CWE-89",)
    assert {"evidence", "validation"} <= set(result.context_bundle)
    assert result.risk_level == "research"
    assert result.execution_required is True


def test_ordinary_development_is_not_routed_as_security_research() -> None:
    result = rewrite_prompt("优化这段 SQL 查询，减少全表扫描并修复参数绑定问题")

    assert result.ordinary_dev is True
    assert result.scene == "general"
    assert result.action_kind == "optimize"
    assert result.risk_level == "low"
    assert result.context_bundle == ("implementation", "benchmark", "tests")


def test_ordinary_development_disambiguation_is_bilingual() -> None:
    result = rewrite_prompt("Optimize this SQL query to reduce full table scans and fix parameter binding issues")

    assert result.ordinary_dev is True
    assert result.action_kind == "optimize"
    assert result.risk_level == "low"


def test_explicit_high_risk_generation_keeps_action_and_is_marked_high() -> None:
    result = rewrite_prompt("生成一个免杀且适配哥斯拉的 webshell")

    assert result.action_kind == "generate"
    assert result.scene == "pentest"
    assert result.risk_level == "high"
    assert "免杀" in result.research_brief
    assert "webshell" in result.research_brief


def test_followup_resumes_existing_goal_instead_of_starting_another_operation() -> None:
    state = RedTeamState(
        objective="验证既有目标",
        operation_run_id="run-1",
        last_scene="web",
        last_action_kind="verify",
        last_risk_level="research",
        last_context_bundle=["defensive_analysis", "evidence", "validation"],
        last_taxonomy=["CWE-89"],
    )

    decision = detect_intent("继续执行并验证结果", state)

    assert decision.intent_type == "continue"
    assert decision.objective_delta == ""
    assert decision.rewrite is not None
    assert decision.rewrite.scene == "web"
    assert decision.rewrite.action_kind == "verify"
    assert decision.rewrite.taxonomy == ("CWE-89",)


def test_explicit_revision_replaces_objective() -> None:
    state = RedTeamState(objective="旧目标")

    decision = detect_intent("目标改为：验证 C:/samples/app.exe", state)

    assert decision.intent_type == "revise"
    assert decision.objective_delta == "验证 C:/samples/app.exe"

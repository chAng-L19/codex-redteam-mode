---
name: redteam-code-audit-detail-pack
description: "Domain routing and boundary guidance for authorized source code security review, including dangerous function tracing, data-flow analysis, logic flaw detection, and dependency review. Use when a task belongs to the code audit domain and needs scope, evidence, pivot, or exit criteria."
---

# 代码审计

## Domain

当前处于 代码审计 领域。
你正在进行源代码安全审计。测试范围仅限白盒代码审计（含危险函数追踪、数据流分析、逻辑漏洞识别、第三方依赖审查等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 注入类 | SQL/CMD/LDAP sink |
| 认证缺陷 | 硬编码/弱校验 |
| 逻辑漏洞 | 竞态/流程跳过 |
| 依赖风险 | 已知 CVE/供应链 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得泄露审计目标的源代码
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 代码量巨大，优先审计入口点（路由/API/用户输入处理）
- 如果 框架封装深，追踪框架安全机制、寻找绕过点
- 如果 依赖复杂，检查已知 CVE、不安全版本、供应链风险
- 如果 未发现高危漏洞，降级审查中低危，汇报回退上级
- 入口点优先 → 危险函数 → 数据流追踪 → 依赖检查 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 漏洞代码位置（文件:行号）
- 数据流路径（source → sink）
- PoC 或利用场景描述
- 修复建议

未发现漏洞时，提交审计报告：已审计范围 + 安全性评估 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

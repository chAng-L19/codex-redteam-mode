---
name: redteam-injection-detail-pack
description: "Domain routing and boundary guidance for authorized general injection testing outside SQL injection, including NoSQL, LDAP, XPath, and expression language injection. Use when a task belongs to the general injection domain and needs scope, evidence, pivot, or exit criteria."
---

# 通用注入测试

## Domain

当前处于 通用注入测试 领域。
你正在进行通用注入漏洞测试。测试范围涵盖非 SQL 注入类别（含 NoSQL 注入、LDAP 注入、XPath 注入、表达式语言注入等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| NoSQL 注入 | MongoDB $ne/$regex |
| LDAP 注入 | )(|(uid=*) |
| XPath 注入 | ' or '1'='1 |
| EL 注入 | ${applicationScope} |
| Header 注入 | CRLF/Host 注入 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得执行破坏性注入操作
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 后端类型未知，使用多种注入探针并行测试（$ne/$gt、*)(|、' or '1'='1）
- 如果 输入严格过滤，编码绕过、Unicode 标准化差异、HPP 参数污染
- 如果 无回显，基于错误/时间的盲注入确认
- 如果 所有注入点均安全，回退到上级知识库重新选择测试方向
- 后端未知 → 多探针 → 编码绕过 → 盲注确认 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整请求（含注入 payload）
- 注入执行成功的证明
- 注入类型标注与影响评估

无法证明漏洞时，提交 negative report：已测试注入点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

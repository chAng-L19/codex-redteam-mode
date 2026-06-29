---
name: redteam-sqli-detail-pack
description: "Domain routing and boundary guidance for authorized SQL injection testing, including union-based, blind, error-based, stacked query, and second-order SQL injection variants. Use when a task belongs to the SQL injection domain and needs scope, evidence, pivot, or exit criteria."
---

# SQL 注入测试

## Domain

当前处于 SQL 注入测试 领域。
你正在进行 SQL 注入漏洞测试。测试范围仅限 SQL 注入（含联合注入、盲注、报错注入、堆叠查询、二次注入等变体）。自主选择注入点和 payload。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|---------|
| 联合注入 (UNION) | SELECT 语句可控列数 |
| 布尔盲注 | 页面差异判断 |
| 时间盲注 | SLEEP/BENCHMARK 延时 |
| 报错注入 | extractvalue/updatexml |
| 堆叠查询 | 多语句执行 |
| 二次注入 | 存储后触发 |
| OOB 外带 | DNS/HTTP 回传 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得执行 DROP/TRUNCATE 等不可恢复的破坏性 SQL
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 WAF / 关键字过滤，尝试编码绕过（双重URL编码、Unicode）、注释分割、大小写混合、内联注释
- 如果 参数化查询无注入点，换其他参数（Header、Cookie、JSON 字段、路径段）
- 如果 所有入口均不可注入，回退到上级知识库重新选择测试方向
- 不要反复尝试同一个失败的 payload 变体
- WAF 拦截 → 编码绕过 → 换注入点 → 换参数位置 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含注入 payload）
- 对应响应（证明 SQL 执行成功的标志：数据泄露/报错信息/延时差异）
- 注入类型标注（联合/盲注/报错/堆叠）与影响简述

无法证明漏洞时，提交 negative report：已测试注入点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-logic-detail-pack
description: "Domain routing and boundary guidance for authorized business logic vulnerability testing, including race conditions, flow bypass, price tampering, permission logic errors, and bulk operation abuse. Use when a task belongs to the logic testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 业务逻辑漏洞测试

## Domain

当前处于 业务逻辑漏洞测试 领域。
你正在进行业务逻辑漏洞测试。测试范围仅限逻辑缺陷（含竞态条件、流程跳过、价格篡改、权限逻辑错误、批量操作滥用等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 竞态条件 | 双重提交/并发消耗 |
| 流程跳过 | 支付步骤绕过 |
| 价格篡改 | 客户端金额修改 |
| 权限逻辑 | 角色检查不完整 |
| IDOR | 对象引用越权 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得造成真实经济损失
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 流程有严格校验，分析状态机、寻找可跳过的中间步骤
- 如果 竞态窗口极小，增加并发线程数、利用 HTTP/2 单包多请求
- 如果 金额/数量有服务端校验，尝试负数、极大数、浮点精度、货币单位混淆
- 如果 所有业务逻辑安全，回退到上级知识库重新选择测试方向
- 校验严格 → 竞态攻击 → 参数篡改 → 流程分析 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整操作步骤序列
- 逻辑缺陷利用成功的证明（余额变化/权限越级/流程绕过）
- 业务影响评估

无法证明漏洞时，提交 negative report：已测试逻辑点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-cache-poison-detail-pack
description: "Domain routing and boundary guidance for authorized web cache poisoning testing, including unkeyed headers, unkeyed parameters, cache deception, and CDN-specific behavior. Use when a task belongs to the cache poisoning domain and needs scope, evidence, pivot, or exit criteria."
---

# 缓存投毒测试

## Domain

当前处于 缓存投毒测试 领域。
你正在进行 Web 缓存投毒测试。测试范围仅限缓存投毒攻击（含 unkeyed header/参数投毒、缓存欺骗、CDN 特有漏洞等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| Header 投毒 | X-Forwarded-Host 注入 |
| 参数投毒 | unkeyed 查询参数 |
| 缓存欺骗 | 路径混淆窃取响应 |
| CDN 差异 | 源站与 CDN 键不同 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对生产缓存执行持久性投毒
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 无法确定缓存键，使用 Param Miner 或手动 Fuzz unkeyed 输入
- 如果 缓存不命中，调整 cache-buster 参数、检查 Vary 头
- 如果 CDN 层缓存规则不同，分别测试源站和 CDN 行为差异
- 如果 所有缓存行为安全，回退到上级知识库重新选择测试方向
- 无 unkeyed 输入 → Param Miner Fuzz → 缓存欺骗路径 → CDN 层测试 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 投毒请求（含 unkeyed 输入）
- 受害者请求获得被投毒响应的证明
- 缓存持久时间与影响范围

无法证明漏洞时，提交 negative report：已测试缓存点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

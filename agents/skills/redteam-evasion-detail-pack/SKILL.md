---
name: redteam-evasion-detail-pack
description: "Domain routing and boundary guidance for authorized defense evasion and bypass testing, including WAF bypass, AV/EDR evasion, logging considerations, and traffic obfuscation. Use when a task belongs to the evasion domain and needs scope, evidence, pivot, or exit criteria."
---

# 防御规避与绕过

## Domain

当前处于 防御规避与绕过 领域。
你正在进行防御规避测试。测试范围仅限安全防护绕过（含 WAF 绕过、AV/EDR 规避、日志清除、流量混淆等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| WAF 绕过 | 编码/分块/HPP |
| AV 规避 | 加载器/内存执行 |
| EDR 绕过 | Unhooking/直接系统调用 |
| 日志规避 | 时间窗口/合法伪装 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得永久禁用目标安全防护设施
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 WAF 规则严格，编码变体、分块传输、HTTP 参数污染、协议层绕过
- 如果 AV/EDR 查杀，加载器混淆、内存执行、合法工具 LOLBins
- 如果 日志监控完善，低频操作、合法流量伪装、时间窗口利用
- 如果 所有规避手段被检测，记录检测机制特征，回退上级
- WAF → 编码变体 → AV → 内存执行 → EDR → syscall → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 规避技术描述与实施步骤
- 绕过成功证明（payload 执行/未触发告警）
- 绕过的防护类型与残余检测能力评估

无法绕过时，提交 negative report：已尝试规避方法 + 检测机制特征 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-web-detail-pack
description: "Routing and boundary guidance for authorized general web application security testing. Use as a web testing router when the attack surface should be dispatched to more specific web vulnerability skills."
---

# Web 综合渗透测试

## Domain

当前处于 Web 综合渗透测试 领域。
你正在进行 Web 应用综合安全测试。本技能作为 Web 测试路由层，根据发现的攻击面分派到具体子域技能。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|----------|
| SQL 注入 | redteam-sqli-detail-pack |
| XSS | redteam-xss-detail-pack |
| SSRF | redteam-ssrf-detail-pack |
| SSTI | redteam-ssti-detail-pack |
| 命令注入 | redteam-cmdi-detail-pack |
| XXE | redteam-xxe-detail-pack |
| 文件操作 | redteam-file-detail-pack |
| 认证 | redteam-auth-detail-pack |
| CSRF | redteam-csrf-detail-pack |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得跳过子域技能直接执行深度攻击
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 攻击面不明确，先完成全面侦察（端点枚举、技术栈识别）
- 如果 多个潜在漏洞类型，按风险优先级逐一分派子域技能
- 如果 子域技能报告 negative，换下一个优先级方向
- 如果 所有方向均 negative，汇总报告，回退上级
- 攻击面不清 → 侦察优先 → 按风险分派子域 → 子域 negative 换方向 → 汇总回退

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 攻击面枚举结果
- 各子域技能测试结果汇总
- 最终漏洞发现或 negative 报告

作为路由层，汇总各子域技能的输出形成综合报告。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

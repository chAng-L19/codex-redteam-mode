---
name: redteam-open-redirect-detail-pack
description: "Domain routing and boundary guidance for authorized open redirect testing, including parameter redirects, meta or JavaScript redirects, and OAuth redirect_uri abuse. Use when a task belongs to the open redirect domain and needs scope, evidence, pivot, or exit criteria."
---

# 开放重定向测试

## Domain

当前处于 开放重定向测试 领域。
你正在进行开放重定向漏洞测试。测试范围仅限 URL 重定向绕过（含参数重定向、Meta/JS 重定向、OAuth redirect_uri 利用等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 参数重定向 | ?url=//evil.com |
| OAuth redirect | redirect_uri 篡改 |
| Meta 刷新 | HTML meta 标签 |
| JS 重定向 | location.href 可控 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得利用重定向对真实用户实施钓鱼
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 URL 白名单验证，尝试 @ 符号、反斜杠、URL 编码、双重编码
- 如果 相对路径限制，尝试协议相对 URL（//evil.com）、路径穿越
- 如果 仅允许同域，寻找子域接管或开放重定向链
- 如果 所有重定向点均安全，回退到上级知识库重新选择测试方向
- 白名单严格 → URL 编码 → 路径混淆 → 链式重定向 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整请求 URL（含重定向 payload）
- 成功跳转到外部域的证明
- 利用场景评估（OAuth token 泄露/钓鱼辅助）

无法证明漏洞时，提交 negative report：已测试重定向点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

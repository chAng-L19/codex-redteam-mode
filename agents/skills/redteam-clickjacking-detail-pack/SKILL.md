---
name: redteam-clickjacking-detail-pack
description: "Domain routing and boundary guidance for authorized clickjacking testing, including missing X-Frame-Options, CSP frame-ancestors bypasses, and drag-and-drop hijacking. Use when a task belongs to the clickjacking domain and needs scope, evidence, pivot, or exit criteria."
---

# Clickjacking 点击劫持测试

## Domain

当前处于 Clickjacking 点击劫持测试 领域。
你正在进行点击劫持漏洞测试。测试范围仅限 Clickjacking（含 X-Frame-Options 缺失、CSP frame-ancestors 绕过、拖放劫持等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 无框架保护 | 直接 iframe 嵌套 |
| 部分保护 | 某些路径遗漏 |
| 拖放劫持 | drag-and-drop 利用 |
| 多步操作 | 多次点击组合 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对真实用户实施点击劫持攻击
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 X-Frame-Options 设置，检查是否所有页面一致、是否有例外页面
- 如果 CSP frame-ancestors，寻找策略不一致的子域或路径
- 如果 JavaScript 防护，检查 framebusting 脚本是否可被 sandbox 属性禁用
- 如果 所有页面均有完善防护，回退到上级知识库重新选择测试方向
- XFO 存在 → 找遗漏路径 → sandbox 绕过 → 子域嵌套 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 点击劫持 PoC HTML（iframe 嵌套目标页面）
- 可在 iframe 中加载的证明截图
- 受影响的敏感操作评估

无法证明漏洞时，提交 negative report：已测试页面列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

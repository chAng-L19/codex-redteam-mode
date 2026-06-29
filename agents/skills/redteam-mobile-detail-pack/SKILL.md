---
name: redteam-mobile-detail-pack
description: "Domain routing and boundary guidance for authorized mobile application security testing, including insecure storage, certificate pinning bypass, exposed components, and binary reverse engineering. Use when a task belongs to the mobile testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 移动应用安全测试

## Domain

当前处于 移动应用安全测试 领域。
你正在进行移动应用安全测试。测试范围仅限移动端漏洞（含不安全存储、证书绑定绕过、组件暴露、二进制逆向等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 不安全存储 | SharedPrefs/Keychain 明文 |
| 证书绕过 | SSL Pinning hook |
| 组件暴露 | exported Activity/Provider |
| 二进制逆向 | 硬编码密钥/算法 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得发布恶意修改版 APP
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 Root/越狱检测，Frida 绕过、Magisk Hide、Objection hooks
- 如果 证书绑定，动态 hook SSL 验证、自定义信任存储
- 如果 代码混淆，使用 jadx/Ghidra 静态分析、运行时 hook 关键方法
- 如果 所有移动端安全措施完善，回退到上级知识库重新选择测试方向
- Root 检测 → Frida 绕过 → 证书 hook → 静态分析 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 漏洞复现步骤（含 Frida 脚本或操作序列）
- 泄露数据/绕过证明截图
- 影响评估（用户数据暴露范围）

无法证明漏洞时，提交 negative report：已测试面列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

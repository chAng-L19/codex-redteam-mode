---
name: redteam-ssrf-detail-pack
description: "Domain routing and boundary guidance for authorized SSRF testing, including basic SSRF, blind SSRF, protocol smuggling, and cloud metadata access paths. Use when a task belongs to the SSRF domain and needs scope, evidence, pivot, or exit criteria."
---

# SSRF 服务端请求伪造测试

## Domain

当前处于 SSRF 服务端请求伪造测试 领域。
你正在进行 SSRF 漏洞测试。测试范围仅限服务端请求伪造（含基础 SSRF、盲 SSRF、协议走私、云元数据访问等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|---------|
| 基础 SSRF | 直接内网访问 |
| 盲 SSRF | OOB 回调确认 |
| 协议走私 | gopher/dict 利用 |
| DNS 重绑定 | 白名单绕过 |
| 云元数据 | AWS/GCP/Azure IMDSv1 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得通过 SSRF 访问非授权的外部系统
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 URL 白名单限制，尝试 DNS 重绑定、URL 解析差异、重定向跳转、IPv6 映射
- 如果 协议限制，换协议（file://、gopher://、dict://）、利用重定向切换协议
- 如果 内网不可达，尝试云元数据（169.254.169.254）、本地服务枚举
- 如果 所有请求点均不可利用，回退到上级知识库重新选择测试方向
- 不要反复尝试同一个失败的绕过方式
- 白名单绕不过 → DNS 重绑定 → 重定向跳转 → 换协议 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含 SSRF payload URL）
- 服务端发起请求的证据（内网响应内容/DNS 回调/延时差异）
- 可达范围评估（内网段、云元数据、本地文件）

无法证明漏洞时，提交 negative report：已测试 URL 参数列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

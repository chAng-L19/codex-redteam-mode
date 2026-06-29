---
name: redteam-csrf-detail-pack
description: "Domain routing and boundary guidance for authorized CSRF testing, including token bypasses, SameSite bypasses, and JSON CSRF. Use when a task belongs to the CSRF testing domain and needs scope, evidence, pivot, or exit criteria."
---

# CSRF 跨站请求伪造测试

## Domain

当前处于 CSRF 跨站请求伪造测试 领域。
你正在进行 CSRF 漏洞测试。测试范围仅限跨站请求伪造（含 Token 绕过、SameSite 绕过、JSON CSRF 等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|--------|
| 无 Token 保护 | 表单直接提交 |
| Token 可绕过 | 删除/置空仍通过 |
| JSON CSRF | Content-Type 限制绕过 |
| SameSite 绕过 | 子域/顶级导航 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对真实用户发起 CSRF 攻击
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 CSRF Token 存在，检查是否可预测、是否绑定会话、删除 Token 是否仍通过
- 如果 SameSite=Strict，寻找子域可控点、利用顶级导航、检查 GET 请求副作用
- 如果 Content-Type 限制，尝试 text/plain、multipart/form-data、fetch redirect
- 如果 Referer 检查，空 Referer（data: URI）、子串匹配绕过
- 如果 所有敏感操作均有完善防护，回退到上级知识库重新选择测试方向
- Token 验证严格 → SameSite 绕过 → Referer 绕过 → 子域利用 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- CSRF PoC HTML（可触发敏感操作）
- 跨域请求成功执行的证明
- 受影响操作与影响评估

无法证明漏洞时，提交 negative report：已测试端点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

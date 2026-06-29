---
name: redteam-cors-miscfg-detail-pack
description: "Domain routing and boundary guidance for authorized CORS misconfiguration testing, including reflected origins, null origins, subdomain trust, and credential exposure. Use when a task belongs to the CORS testing domain and needs scope, evidence, pivot, or exit criteria."
---

# CORS 配置错误测试

## Domain

当前处于 CORS 配置错误测试 领域。
你正在进行 CORS 配置安全测试。测试范围仅限跨域资源共享配置错误（含 Origin 反射、null 允许、子域信任、凭据泄露等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| Origin 反射 | 任意 Origin 回显 |
| null 允许 | sandbox iframe 利用 |
| 子域信任 | XSS+CORS 组合 |
| 通配符+凭据 | 配置矛盾利用 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得利用 CORS 漏洞窃取真实用户数据
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 Origin 白名单严格，尝试子域、特殊前缀/后缀、null Origin
- 如果 无 credentials 标志，评估是否仍可泄露非敏感数据
- 如果 预检请求阻断，检查简单请求是否绕过
- 如果 所有端点 CORS 配置安全，回退到上级知识库重新选择测试方向
- 白名单严格 → null Origin → 子域 XSS → 前缀匹配 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 恶意 Origin 请求与响应头（Access-Control-Allow-*）
- 跨域数据读取 PoC
- 可泄露数据范围评估

无法证明漏洞时，提交 negative report：已测试端点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

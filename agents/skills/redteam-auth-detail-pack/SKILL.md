---
name: redteam-auth-detail-pack
description: "Domain routing and boundary guidance for authorized authentication, authorization, and session security testing, including password policy, JWT/token, OAuth, and MFA bypass issues. Use when a task belongs to the auth testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 认证与授权漏洞测试

## Domain

当前处于 认证与授权漏洞测试 领域。
你正在进行认证与会话安全测试。测试范围仅限认证机制漏洞（含密码策略、会话管理、JWT/Token、OAuth、MFA 绕过等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|---------|--------|
| 弱密码策略 | 暴力破解/凭据填充 |
| JWT 缺陷 | alg:none/密钥混淆 |
| OAuth 缺陷 | redirect_uri 篡改/CSRF |
| 会话固定 | 登录前后 session 不变 |
| MFA 绕过 | 状态跳过/竞态 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对真实用户账户执行锁定攻击
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 登录有速率限制，IP 轮换、分布式低速尝试、尝试其他认证端点
- 如果 JWT 签名验证严格，检查 alg:none、密钥混淆(RS→HS)、kid 注入、jwk 注入
- 如果 MFA 启用，检查 MFA 绕过（状态跳过、备用码泄露、竞态条件）
- 如果 会话管理安全，检查固定会话、Token 泄露、并发会话控制
- 如果 所有认证流程均安全，回退到上级知识库重新选择测试方向
- 不要反复尝试同一个失败的攻击向量
- 速率限制 → 换端点 → JWT 攻击 → OAuth 流程 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整认证绕过请求链
- 绕过成功证明（获取会话/访问受保护资源）
- 漏洞类型标注与影响范围

无法证明漏洞时，提交 negative report：已测试认证点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-subdomain-takeover-detail-pack
description: "Domain routing and boundary guidance for authorized subdomain takeover testing, including dangling CNAME records, NS takeover, and cloud service takeover paths such as S3, Azure, and Heroku. Use when a task belongs to the subdomain takeover domain and needs scope, evidence, pivot, or exit criteria."
---

# 子域名接管测试

## Domain

当前处于 子域名接管测试 领域。
你正在进行子域接管漏洞测试。测试范围仅限子域名接管（含 CNAME 悬挂、NS 接管、S3/Azure/Heroku 等云服务接管）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| CNAME 悬挂 | 指向已删除服务 |
| NS 接管 | 名称服务器过期 |
| 云服务 | S3/Azure/Heroku/GitHub |
| 边缘情况 | 部分服务商特殊行为 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得实际注册接管域名用于恶意目的
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 CNAME 指向活跃服务，检查是否有条件触发 404/接管页面
- 如果 云服务已声明，尝试同区域同名注册、检查多地域差异
- 如果 DNS 记录无悬挂，扩大子域枚举范围、检查历史记录
- 如果 所有子域均安全，汇报回退上级
- 无悬挂 → 扩大枚举 → 历史记录 → 多地域检查 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 悬挂 DNS 记录（CNAME/NS 指向未声明资源）
- 接管可行性证明（服务注册页面/错误信息）
- 接管后影响评估（cookie 范围/同源策略）

无法接管时，提交 negative report：已检查子域列表 + 状态 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

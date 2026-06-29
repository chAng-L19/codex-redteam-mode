---
name: redteam-api-detail-pack
description: "Domain routing and boundary guidance for authorized API security testing, including BOLA/IDOR, authentication bypass, mass assignment, missing rate limits, and GraphQL issues. Use when a task belongs to the API testing domain and needs scope, evidence, pivot, or exit criteria."
---

# API 安全测试

## Domain

当前处于 API 安全测试 领域。
你正在进行 API 安全测试。测试范围仅限 API 漏洞（含 BOLA/IDOR、认证绕过、批量分配、速率限制缺失、GraphQL 漏洞等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| BOLA/IDOR | 水平越权 |
| 批量分配 | 未过滤字段提权 |
| 认证绕过 | JWT/Token 缺陷 |
| GraphQL | 嵌套查询/泄露 |
| 速率缺失 | 枚举/爆破 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得删除或修改生产数据
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 接口鉴权严格，枚举隐藏端点、尝试低权限越权、检查旧版本 API
- 如果 参数未知，Fuzz 常见参数名、分析前端 JS、检查 OpenAPI/Swagger 文档
- 如果 速率限制，轮换 Token、降低请求频率、尝试批量端点
- 如果 GraphQL 内省被禁，字段建议、错误泄露 schema
- 如果 所有入口均不可利用，回退到上级知识库重新选择测试方向
- 鉴权严格 → 隐藏端点 → 旧版 API → 前端分析 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含 payload）
- 越权/泄露成功的证明
- 漏洞类型标注与影响简述

无法证明漏洞时，提交 negative report：已测试端点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-xxe-detail-pack
description: "Domain routing and boundary guidance for authorized XXE testing, including file read, SSRF, blind XXE, and parameter entity variants. Use when a task belongs to the XXE domain and needs scope, evidence, pivot, or exit criteria."
---

# XXE XML 外部实体注入测试

## Domain

当前处于 XXE XML 外部实体注入测试 领域。
你正在进行 XXE 漏洞测试。测试范围仅限 XML 外部实体注入（含文件读取、SSRF、盲 XXE、参数实体等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|---------|
| 经典 XXE | 外部实体文件读取 |
| 盲 XXE | OOB 外带数据 |
| 参数实体 | DTD 内嵌套利用 |
| XInclude | 非 DTD 环境注入 |
| SVG/DOCX XXE | 文件上传触发 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得通过 XXE 读取非授权系统文件
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 DTD 被禁用，尝试 XInclude、SVG/XSLT 中嵌入实体
- 如果 外部实体被阻止，尝试参数实体、本地 DTD 覆盖
- 如果 无回显，盲 XXE + OOB HTTP/FTP/DNS 外带
- 如果 XML 解析器严格，尝试编码变体（UTF-16/UTF-7）、BOM 头
- 如果 所有 XML 入口均安全，回退到上级知识库重新选择测试方向
- DTD 被禁 → XInclude → SVG 上传 → 盲 XXE OOB → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含 XXE payload XML）
- 实体解析证明（文件内容/SSRF 回调/OOB 数据）
- 可读取范围评估（文件系统/内网/云元数据）

无法证明漏洞时，提交 negative report：已测试 XML 入口列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

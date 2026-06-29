---
name: redteam-file-detail-pack
description: "Domain routing and boundary guidance for authorized file operation vulnerability testing, including path traversal, arbitrary file read/write/upload, and LFI/RFI. Use when a task belongs to the file vulnerability domain and needs scope, evidence, pivot, or exit criteria."
---

# 文件上传/包含/读取漏洞测试

## Domain

当前处于 文件上传/包含/读取漏洞测试 领域。
你正在进行文件操作漏洞测试。测试范围仅限文件相关漏洞（含路径穿越、任意文件读取/写入/上传、文件包含 LFI/RFI 等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 路径穿越 | ../../../etc/passwd |
| LFI | include 本地文件 |
| RFI | include 远程文件 |
| 任意上传 | webshell 上传 |
| 文件覆盖 | 写入配置文件 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得覆盖关键系统文件
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 路径过滤，双重编码、..\\替代、截断（%00）、超长路径
- 如果 文件上传限制，绕过扩展名检查（双扩展、大小写、.htaccess）、Content-Type 篡改
- 如果 文件包含有白名单，利用日志文件包含、session 文件、/proc/self/environ
- 如果 所有文件操作均安全，回退到上级知识库重新选择测试方向
- 路径过滤 → 编码绕过 → 日志包含 → 上传绕过 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整请求（含路径穿越/上传 payload）
- 文件读取/写入/执行成功的证明
- 可访问文件范围与影响评估

无法证明漏洞时，提交 negative report：已测试文件参数列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

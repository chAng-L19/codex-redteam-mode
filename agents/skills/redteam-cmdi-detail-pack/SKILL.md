---
name: redteam-cmdi-detail-pack
description: "Domain routing and boundary guidance for authorized operating system command injection testing, including direct injection, blind injection, out-of-band callbacks, and argument injection. Use when a task belongs to the command injection domain and needs scope, evidence, pivot, or exit criteria."
---

# OS 命令注入测试

## Domain

当前处于 OS 命令注入测试 领域。
你正在进行操作系统命令注入测试。测试范围仅限命令注入（含直接注入、盲注入、OOB 外带、参数注入等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|---------|
| 直接注入 | 命令拼接可控 |
| 盲注入 | 延时/OOB 确认 |
| 参数注入 | --flag 注入 |
| 环境变量注入 | env 覆盖 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得执行 rm -rf / format 等破坏性系统命令
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 命令分隔符被过滤，尝试换行符、$()替换、反引号、%0a 编码
- 如果 空格被禁，使用 $IFS、{cmd,arg}、tab 替代
- 如果 命令黑名单，用通配符(c?t /etc/p?sswd)、变量拼接、base64 编码执行
- 如果 无回显，DNS 外带、延时判断、写文件到 web 目录
- 如果 所有入口均不可注入，回退到上级知识库重新选择测试方向
- 分隔符被禁 → 换编码 → 无回显走 OOB → 参数注入 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含命令注入 payload）
- 命令执行证明（回显输出/DNS 回调/延时差异/文件创建）
- 注入类型标注与权限级别评估

无法证明漏洞时，提交 negative report：已测试参数列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

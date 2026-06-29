---
name: redteam-ssti-detail-pack
description: "Domain routing and boundary guidance for authorized server-side template injection testing, including Jinja2, Twig, Freemarker, Velocity, and Thymeleaf engines. Use when a task belongs to the SSTI domain and needs scope, evidence, pivot, or exit criteria."
---

# SSTI 服务端模板注入测试

## Domain

当前处于 SSTI 服务端模板注入测试 领域。
你正在进行服务端模板注入测试。测试范围仅限 SSTI（含 Jinja2、Twig、Freemarker、Velocity、Thymeleaf 等模板引擎）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|------------|
| Jinja2 | {{config.__class__.__init__.__globals__}} |
| Twig | {{_self.env.registerUndefinedFilterCallback}} |
| Freemarker | <#assign ex="freemarker.template.utility.Execute"?new()> |
| Velocity | #set($x='')#set($rt=$x.class.forName('java.lang.Runtime')) |
| Thymeleaf | __${T(java.lang.Runtime).getRuntime().exec('id')}__ |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得通过 RCE 执行破坏性系统命令
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 模板引擎未知，使用探测 payload（{{7*7}}、${7*7}、<%= 7*7 %>）识别引擎
- 如果 沙箱限制，尝试 MRO 链遍历、内置对象逃逸、已知 gadget chain
- 如果 输入被过滤，编码绕过、字符串拼接、属性访问替代语法
- 如果 所有模板点均安全，回退到上级知识库重新选择测试方向
- 不要反复尝试同一个失败的 payload
- 探测无回显 → 盲注时间差 → 换探测语法 → 尝试其他参数 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求（含模板注入 payload）
- 模板执行证明（计算结果/命令输出/文件读取）
- 引擎类型标注与 RCE 可行性评估

无法证明漏洞时，提交 negative report：已测试模板点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

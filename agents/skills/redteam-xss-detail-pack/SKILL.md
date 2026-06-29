---
name: redteam-xss-detail-pack
description: "Domain routing and boundary guidance for authorized cross-site scripting testing, including reflected, stored, DOM-based, mXSS, and CSP bypass variants. Use when a task belongs to the XSS domain and needs scope, evidence, pivot, or exit criteria."
---

# XSS 跨站脚本测试

## Domain

当前处于 XSS 跨站脚本测试 领域。
你正在进行 XSS 漏洞测试。测试范围仅限跨站脚本攻击（含反射型、存储型、DOM 型、mXSS、CSP 绕过等变体）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

| 变体 | 典型场景 |
|------|---------|
| 反射型 XSS | URL 参数回显 |
| 存储型 XSS | 评论/个人资料持久化 |
| DOM 型 XSS | JS sink/source 链 |
| mXSS | 解析器差异利用 |
| CSP 绕过 | JSONP/trusted-types |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对其他用户发起真实钓鱼攻击
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 输入过滤/编码，尝试 HTML 实体绕过、事件处理器、SVG/MathML 标签、模板字面量
- 如果 CSP 严格，寻找 JSONP 端点、unsafe-eval gadget、base-uri 未限制、可信域资源
- 如果 框架自动转义，寻找 dangerouslySetInnerHTML / v-html / [innerHTML] 等 sink
- 如果 所有反射点均被安全处理，回退到上级知识库重新选择测试方向
- 不要反复尝试同一个失败的 payload 变体
- 过滤绕不过 → 换标签/事件 → 找 DOM sink → CSP gadget → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整 HTTP 请求或 DOM 操作步骤（含 XSS payload）
- 脚本执行证明（alert/console/cookie 访问截图）
- XSS 类型标注（反射/存储/DOM）与影响简述（会话劫持/数据窃取可行性）

无法证明漏洞时，提交 negative report：已测试反射点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

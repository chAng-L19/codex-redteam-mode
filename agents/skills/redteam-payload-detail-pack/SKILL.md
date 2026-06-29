---
name: redteam-payload-detail-pack
description: "Domain routing and boundary guidance for authorized payload construction and weaponization analysis, including shellcode, file format payloads, phishing payloads, and staged or stageless payload choices. Use when a task belongs to the payload construction domain and needs scope, evidence, pivot, or exit criteria."
---

# Payload 构造与武器化

## Domain

当前处于 Payload 构造与武器化 领域。
你正在进行 Payload 生成与投递测试。测试范围仅限载荷构造（含 shellcode 生成、文件格式利用、钓鱼载荷、staged/stageless 等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| Shellcode | 编码/加密/syscall |
| 文件格式 | 宏/LNK/ISO/PDF |
| 钓鱼载荷 | HTML smuggling |
| Staged | 分阶段加载 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得向非授权目标投递载荷
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 文件格式被检测，修改 magic bytes、加密内嵌、利用合法格式特性
- 如果 Shellcode 被查杀，编码/加密/自解密、syscall 直调用
- 如果 投递渠道被阻，换投递方式（宏/LNK/ISO/OneNote）、利用信任关系
- 如果 所有载荷被拦截，记录检测规则特征，回退上级
- 被查杀 → 换编码 → 换格式 → 换投递渠道 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- Payload 构造方法与工具
- 投递成功并执行的证明
- 绕过的检测层与残余风险

无法投递成功时，提交 negative report：已尝试载荷类型 + 被拦截环节 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

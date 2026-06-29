---
name: redteam-reverse-detail-pack
description: "Domain routing and boundary guidance for authorized reverse engineering analysis, including decompilation, debugging, protocol reversing, firmware extraction, and deobfuscation. Use when a task belongs to the reverse engineering domain and needs scope, evidence, pivot, or exit criteria."
---

# 逆向工程分析

## Domain

当前处于 逆向工程分析 领域。
你正在进行逆向工程分析。测试范围仅限二进制逆向（含反编译、调试、协议逆向、固件提取、反混淆等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 反编译 | Java/IL/.NET |
| 原生逆向 | x86/ARM IDA/Ghidra |
| 协议逆向 | 自定义协议分析 |
| 固件提取 | binwalk/文件系统 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得分发逆向得到的知识产权内容
- 不得超出授权目标范围
- 不得伪造或夸大发现结果
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 反调试保护，patch 反调试检查、使用硬件断点、内核调试
- 如果 代码混淆严重，符号恢复、模式匹配、动态跟踪关键调用
- 如果 加壳保护，dump 运行时内存、识别壳类型针对性脱壳
- 如果 所有保护无法绕过，记录已尝试方法，回退上级
- 反调试 → patch/硬件断点 → 混淆 → 动态跟踪 → 脱壳 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 逆向分析报告（关键函数/协议/算法）
- 发现的安全缺陷（硬编码凭据/后门/弱算法）
- 利用可行性评估

无法发现缺陷时，提交分析报告：已逆向范围 + 安全性评估 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

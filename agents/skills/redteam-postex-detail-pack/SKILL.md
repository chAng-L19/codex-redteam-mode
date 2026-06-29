---
name: redteam-postex-detail-pack
description: "Domain routing and boundary guidance for authorized post-exploitation testing after initial access, including privilege escalation, persistence, lateral movement, data collection, and cleanup considerations. Use when a task belongs to the post-exploitation domain and needs scope, evidence, pivot, or exit criteria."
---

# 后渗透利用

## Domain

当前处于 后渗透利用 领域。
你正在进行后渗透阶段测试。测试范围仅限获得初始访问后的操作（含权限提升、持久化、横向移动、数据收集、痕迹清除等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 本地提权 | 内核/SUID/服务错配 |
| 持久化 | 定时任务/启动项/后门 |
| 横向移动 | PTH/PTT/WMI |
| 数据收集 | 凭据/文件/数据库 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对生产系统造成不可恢复的损害
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 本地提权受限，检查内核版本 CVE、SUID 文件、服务错配、定时任务
- 如果 EDR 监控进程，LOLBins、内存操作、合法工具代理
- 如果 横向移动被阻，换协议（WMI/SSH/RDP）、利用信任关系、票据传递
- 如果 无法进一步深入，固化当前权限，汇报回退上级
- 提权失败 → 换 CVE → 服务错配 → SUID → 固化当前 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 权限提升/横向移动完整路径
- 获得的最高权限证明
- 可控资产范围与数据访问评估

无法进一步提升时，提交当前访问报告：已获权限 + 受阻点 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

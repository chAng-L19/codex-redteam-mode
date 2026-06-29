---
name: redteam-ad-detail-pack
description: "Domain routing and boundary guidance for authorized Active Directory red-team security testing, including Kerberos attacks, domain privilege escalation, lateral movement, and GPO abuse. Use when a task belongs to the AD testing domain and needs scope, evidence, pivot, or exit criteria."
---

# Active Directory 域渗透

## Domain

当前处于 Active Directory 域渗透 领域。
你正在进行 Active Directory 域渗透测试。测试范围仅限 AD 环境攻击（含 Kerberos 攻击、域提权、横向移动、GPO 滥用等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|---------|--------|
| Kerberoasting | SPN 弱密码 |
| AS-REP Roasting | 无预认证账户 |
| DCSync | 高权限凭据复制 |
| Golden/Silver Ticket | 域持久化 |
| GPO 滥用 | 策略权限提升 |
| NTLM Relay | 中继认证 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对生产域控执行不可恢复的破坏性操作
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 域控不可达，检查网络分段，尝试中继攻击或寻找域内跳板
- 如果 Kerberos 票据获取失败，尝试 AS-REP Roasting、密码喷射、NTLM 降级
- 如果 提权路径不通，枚举 ACL/GPO 权限、寻找 Unconstrained Delegation
- 如果 横向移动被阻，尝试 WMI/DCOM/WinRM 替代协议、PTH/PTT
- 如果 所有路径均失败，回退到上级知识库重新选择攻击面
- DC 不可达 → 中继攻击 → BloodHound 分析 → 密码喷射 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 完整攻击链命令序列
- 域环境信息（域名、DC 版本、当前权限）
- 攻击成功标志（获取票据/hash/shell）
- 影响简述（提权路径、横向范围）

无法证明漏洞时，提交 negative report：已测试攻击路径列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

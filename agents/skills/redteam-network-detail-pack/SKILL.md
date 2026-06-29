---
name: redteam-network-detail-pack
description: "Domain routing and boundary guidance for authorized network-layer security testing, including exposed services, protocol downgrade, man-in-the-middle risks, and segmentation bypasses. Use when a task belongs to the network testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 网络层渗透测试

## Domain

当前处于 网络层渗透测试 领域。
你正在进行网络层安全测试。测试范围仅限网络漏洞（含端口/服务暴露、协议降级、中间人、网络分段绕过等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 服务暴露 | 未授权访问(Redis/MongoDB) |
| 协议降级 | TLS→明文 |
| ARP/DNS 欺骗 | 中间人攻击 |
| 网段穿透 | 跳板横向移动 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对非授权网段发起扫描
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 防火墙严格，检查非标端口、UDP 服务、IPv6 双栈
- 如果 IDS/IPS 阻断，降低扫描速率、分片、加密隧道
- 如果 网络分段，寻找双网卡主机、VPN 隧道、管理网入口
- 如果 所有网络配置安全，回退到上级知识库重新选择测试方向
- 防火墙 → 非标端口 → UDP 服务 → IPv6 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 网络拓扑发现结果
- 可利用服务/协议的证明
- 横向可达范围与影响评估

无法证明漏洞时，提交 negative report：已探测服务列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

---
name: redteam-recon-detail-pack
description: "Domain routing and boundary guidance for authorized reconnaissance and information gathering, including subdomain enumeration, port scanning, directory discovery, fingerprinting, and OSINT. Use when a task belongs to the recon domain and needs scope, evidence, pivot, or exit criteria."
---

# 信息收集与侦察

## Domain

当前处于 信息收集与侦察 领域。
你正在进行信息收集与侦察。测试范围仅限被动和主动侦察（含子域枚举、端口扫描、目录发现、指纹识别、OSINT 等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 子域枚举 | DNS/CT/爆破 |
| 端口扫描 | TCP/UDP 全端口 |
| 目录发现 | 敏感路径/备份文件 |
| 指纹识别 | CMS/框架/版本 |
| OSINT | 邮箱/员工/泄露凭据 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得对非授权资产进行主动扫描
- 不得超出授权目标范围
- 不得伪造或夸大发现结果
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 CDN/WAF 隐藏真实 IP，历史 DNS 记录、邮件头、证书搜索
- 如果 子域枚举受限，证书透明度、DNS 区域传送、关联域反查
- 如果 目录扫描被封，降速、换 User-Agent、使用自定义字典
- 如果 信息收集饱和，整理已有信息，交付给对应攻击模块
- CDN 遮挡 → 历史记录 → 证书搜索 → 邮件头 → 整理交付

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 资产清单（域名/IP/端口/服务）
- 关键发现（敏感文件/版本信息/技术栈）
- 建议攻击面与优先级排序

侦察完成后交付资产清单给上级进行攻击路径分配。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

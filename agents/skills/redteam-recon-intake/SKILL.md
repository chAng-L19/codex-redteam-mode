---
name: redteam-recon-intake
description: "Recon intake skill for first contact with a bare domain, URL, or IP address. Use to build an initial recon_profile and provide factual inputs for CVE lookup and attack-path routing."
---

# Recon Intake

## Domain

裸域名/URL/IP 首次进入安全评估时的侦察入口。
负责从零建立目标资产画像(recon_profile)，为后续 CVE Lookup 和攻击路径分配提供事实依据。

阶段顺序：
1. DNS 解析 + 存活探测
2. 端口扫描 + 服务指纹
3. 子域枚举
4. Web 目录/敏感文件探测
5. WAF/CDN 识别
6. 技术栈指纹(CMS/框架/中间件版本)

## Boundaries

- 不执行任何主动漏洞利用
- 不发送破坏性请求(DELETE/DROP/shutdown)
- 不对非授权范围外的域名/IP 进行探测
- 不进行暴力破解或密码喷洒
- 不绕过速率限制(如被限速则降速或暂停)
- 侦察深度止于信息收集，不进入漏洞验证阶段

## Pivot Hints

- WAF/CDN 阻断直连 → 尝试历史 DNS、邮件头、证书搜索获取真实 IP
- 子域枚举受限 → 证书透明度日志、DNS 区域传送、关联域反查
- 目录扫描被封 → 降速、换 User-Agent、使用自定义字典
- 端口全部过滤 → 检查 IPv6、尝试常见高端口、确认目标存活
- 信息收集饱和 → 整理已有信息，输出 recon_profile 并推进到下一阶段

## Exit Evidence

- Required: recon_profile, port_scan_result, service_fingerprint
- min_attempts: 4

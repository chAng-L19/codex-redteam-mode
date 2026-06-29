---
name: redteam-crypto-detail-pack
description: "Domain routing and boundary guidance for authorized cryptography weakness testing, including weak algorithms, padding oracles, key management errors, insecure randomness, and hash collision risks. Use when a task belongs to the cryptography testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 密码学弱点测试

## Domain

当前处于 密码学弱点测试 领域。
你正在进行密码学实现漏洞测试。测试范围仅限加密缺陷（含弱算法、填充 oracle、密钥管理、随机数不安全、哈希碰撞等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| 弱算法 | DES/RC4/MD5 使用 |
| 填充 Oracle | CBC padding 泄露 |
| ECB 模式 | 块重排攻击 |
| 弱随机数 | 可预测 token |
| 密钥硬编码 | 源码/配置泄露 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得尝试破解非授权系统的密钥
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 算法看似安全，检查实现细节（ECB 模式、固定 IV、密钥复用）
- 如果 无法直接观察解密，尝试填充 oracle（错误信息差异/时间差异）
- 如果 密钥存储不可达，检查配置文件、环境变量、硬编码
- 如果 所有密码学实现安全，回退到上级知识库重新选择测试方向
- 算法安全 → 检查实现 → 填充 oracle → 密钥管理 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 密码学缺陷描述与利用步骤
- 解密/伪造/碰撞成功的证明
- 影响评估（可伪造范围/可解密数据）

无法证明漏洞时，提交 negative report：已测试加密点列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

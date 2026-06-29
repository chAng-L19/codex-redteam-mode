---
name: red-team-command-doctrine
description: "Governance skill for red-team mode phase selection, router selection, detailed pack selection, OPSEC-aware progression, and choosing the next concrete skill. Use when red-team mode needs command-level decision support before technical testing."
---

# 红队指挥决策

## Domain

当前处于红队指挥决策领域。
本 skill 是攻击阶段选择、路由决策、详细包选择和 OPSEC 感知推进的紧凑治理技能。
在红队模式激活时使用此 skill 进行阶段/路由决策。它不直接执行攻击，只负责选择正确的阶段、路由和叶子技能。

阶段矩阵：

| Phase | Goal | Typical Router | Exit Signal |
|---|---|---|---|
| recon | 建立目标画像 | recon-for-sec | 足够证据选择一条候选路径 |
| web | 证明一条 web 攻击路径 | auth-sec / api-sec / injection-checking | 一条可复现路径或排除分支 |
| ad | 选择最安静的域路径 | AD routers | 一条有证据的可行域路径 |
| postex | 分类立足点和下一跳 | post-exploitation-playbook | 下一跳或目标已识别 |
| reverse | 恢复执行链 | malware-loader-analysis | 执行链或可利用性已澄清 |
| code-audit | 证明一条输入到 sink 的链 | auth-sec / api-sec / injection-checking | 一条受控路径已演示 |
| payload | 塑造投递 | weaponization-and-payloads | 投递约束已匹配 |
| evasion | 选择最低噪声绕过 | windows-av-evasion | 绕过路线已选择或已排除 |

路由规则：phase → router → leaf skill

方法层默认映射：
- web/ad/reverse/code-audit → investigation-first
- postex → concentrate-forces
- payload/evasion → practice-cognition
- 多路径竞争时升级到 contradiction-analysis
- 需集中主攻时升级到 concentrate-forces

## Boundaries

- 不得跳过阶段判断直接进入攻击。
- 不得无视 OPSEC 检查清单。
- 不得伪造阶段完成标志。
- 不在缺少证据时声明阶段完成。
- 不超出授权目标范围。
- 不把候选路径等同于已验证路径。
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only。

## Pivot Hints

- 如果当前阶段缺少退出证据，补齐最小必要上下文再判断。
- 如果多条路径竞争，使用 contradiction-analysis 选择主要矛盾。
- 如果任务跨多阶段，切换到结构化编排（recon→strategy→exploit-dev→review→reporting）。
- 如果技术路径已可见，优先选择匹配的 detail-pack 而非抽象方法论。
- 如果检测面过大，优先选择低噪声路径。
- 如果被中断，确认当前状态可恢复后再继续。

## OPSEC Gates

每次行动前检查：
1. 是否存在更低噪声的路径可以先证明？
2. 是否在没有新证据的情况下扩大范围？
3. 此动作是否会生成可避免的日志、认证事件或扫描？
4. 能否使用原生证据（Burp、CLI、主机事实）而非假设？
5. 下一步是否直接关联目标？
6. 是否会烧掉当前访问、凭据或基础设施？
7. 预期收益是否证明检测面合理？
8. 如果现在中断，当前状态是否可恢复？

## Exit Evidence

Required artifacts:
- phase_selection
- route_decision

Minimum attempts for negative result: 2

Positive exit requires:
- 阶段选择有明确证据支撑。
- 路由决策基于目标特征而非猜测。
- 选定的 leaf skill 与当前证据匹配。

Negative exit requires:
- 记录已评估的阶段和路由。
- 记录为什么无法选定路径。
- 不声明目标不可攻击，只声明当前证据下无法选定攻击路径。

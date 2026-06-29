---
name: redteam-container-detail-pack
description: "Domain routing and boundary guidance for authorized container and orchestration security testing, including Docker escape, Kubernetes privilege escalation, image vulnerabilities, and service mesh bypasses. Use when a task belongs to the container testing domain and needs scope, evidence, pivot, or exit criteria."
---

# 容器安全测试

## Domain

当前处于 容器安全测试 领域。
你正在进行容器安全测试。测试范围仅限容器逃逸与编排平台漏洞（含 Docker 逃逸、K8s 提权、镜像漏洞、Service Mesh 绕过等）。
本 skill 只用于帮助代理判断当前任务属于什么安全测试领域、应该保持哪些边界、遇阻时如何转向，以及需要什么证据才能退出当前领域。
它不是方法论教程，不提供固定攻击步骤，不替代用户授权范围，也不把任何推测当作结论。

覆盖域：

|------|--------|
| Docker 逃逸 | 特权模式/挂载卷 |
| K8s 提权 | RBAC/SA token |
| 镜像漏洞 | 已知 CVE 利用 |
| 网络策略 | Pod 间未隔离 |

## Boundaries

- 只围绕用户明确提供或授权的目标工作。
- 不超出当前目标、域名、IP、应用、代码库或系统边界。
- 不伪造、不夸大、不补写不存在的证据。
- 不在缺少证据时声明任务完成。
- 不把候选风险、公开 CVE、组件指纹直接等同于可利用漏洞。
- 不得破坏生产容器编排状态
- 不得超出授权目标范围
- 不得伪造或夸大漏洞证据
- 如果 scope、target 或授权边界不明确，进入 blocked 或 plan-only，不进行真实执行。

## Pivot Hints

- 如果 容器已加固（无 privileged），检查 capabilities、挂载卷、proc/sys 可写性
- 如果 K8s RBAC 严格，枚举 ServiceAccount 权限、检查 secrets 可读性
- 如果 Seccomp/AppArmor 限制，寻找允许的 syscall 利用路径
- 如果 所有容器配置均安全，回退到上级知识库重新选择测试方向
- 无特权 → capabilities 检查 → 挂载利用 → SA 枚举 → 回退上级

## Exit Evidence

Required artifacts:
- reproduction

Minimum attempts for negative result: 3

Positive exit requires:
- 关键结论至少有 supported 级证据。
- 漏洞成立、影响判断或最终报告必须有 verified 级证据。
- artifact 能说明来源、目标、时间、观察结果和判断依据。

reproduction 证据须包含：
- 逃逸/提权完整命令链
- 宿主机访问或集群权限提升证明
- 影响范围（可达节点/命名空间）

无法证明漏洞时，提交 negative report：已测试路径列表 + 失败原因 → 回退上级。

Negative exit requires:
- 达到最小尝试次数。
- 记录已尝试路径。
- 记录未发现证据的原因。
- 不输出"确认不存在"，只输出"当前证据下未发现"。

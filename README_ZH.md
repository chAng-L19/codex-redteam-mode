# Codex 红队 Opt-In 模式

[English](./README.md)

**当前版本：** v1.1.0

> 默认 normal 模式。红队模式必须显式开启；一旦进入红队模式，自动化能力默认自动启动。

一个轻量级、证据驱动的红队运行时/配置层，用于 Codex。普通编码、文档、研究任务默认保持 normal 模式；只有用户明确触发红队模式后，才启用 Loop Runtime SKILL.md 领域卡系统、5-Phase 引擎、分级反馈门和自动化规划。

## 项目初衷

AI 辅助安全工作中有两个常见陷阱：

1. **污染正常操作** — 持续存在的红队提示或系统指令渗透到日常编码中，导致不必要的拒绝或异常行为。
2. **上下文膨胀** — 大量注入攻击方法论增加了 token 消耗，却没有真正提升路由质量。

本项目的解决方式：**normal 模式保持纯净**，红队模式必须显式开启。开启后，通过 SKILL.md Loop Runtime 领域卡声明领域范围、边界约束和退出证据要求，由 5-Phase 引擎按证据驱动推进——而不是一次性倾泻大量提示。

## 核心特性

- **三种显式模式**：`normal`（默认）、`redteam-light`（定向分析/规划）、`redteam-full`（受限的红队工作流）
- **结构化 JSON 运行状态**，session 隔离的状态文件
- **规则优先的 phase 检测**，语义判断作为模糊任务的 fallback
- **Pack-first 路由主线**：`phase → router → pack → leaf` — method 仅作为软提示，不是主路由轴
- **专用路由层** — 基于正则的路由引擎（中英文模式匹配），按领域细分的子路由器（5 个 Web、4 个 AD、6 个 Crypto、5 个 Network、3 个 Mobile），外部技能适配器（ACS/hackskills/qiushi）；路由层重构覆盖全部 13 个 phase，32 条 router→pack 映射
- **SKILL.md Loop Runtime 领域卡** — 纯 Markdown `scope-not-instruct` 模式：每张卡片通过 `## Domain`（领域声明）、`## Boundaries`（禁止操作）、`## Pivot Hints`（转向提示）、`## Exit Evidence`（退出证据）四节定义 AI 在哪个领域工作、什么不能做、什么条件下退出，不规定具体做法
- **5-Phase 引擎** — `controller.py` 编排 intent → phase routing → SKILL.md → taskbook → loop decision 全流程；分级反馈门（pass / soft_fail / pivot / blocked）驱动推进；`phase_drive` 实现 recon → strategy → testing → reporting 四阶段工作流
- **证据 Artifact 追踪** — 类型化、可验证的 `EvidenceArtifact` 对象（`enumeration`、`reproduction`、`impact`），驱动 gate 式推进
- **轻量 hooks** — 激活引擎、上下文预处理、意图引擎、循环引擎、phase 检测、语义 fallback、状态管理、拒答回退
- **Session 修补器** — 两级拒答检测（强短语 + 弱开头词，中英文双语），JSONL session 文件清理，自动备份，可选 AI 改写回退
- **有界 Loop Runtime** — 每次决策都包含触发器、反馈门和退出条件，用于根据证据调整节奏
- **Artifact/gate 证据推进机制** — 区分事实与假设，以证据链驱动执行连续性
- **自动化 Loop Runtime** — 读取本地 MCP/工具清单，推导所需能力，执行 scoped registered adapter，保存 artifact，并回灌 gate 判定
- **工具优先级模型**：优先 5 类实战工具（WebFetch、Browser MCP、IDA MCP、JADX MCP、当前使用的 AI），缺失时回退到同等能力的本地工具
- **增量安装器** — 基于 Python，保留已有 AGENTS.md 和 hooks.json，仅注入受管控块，支持 `--uninstall` 和幂等升级

## 覆盖场景

### 核心 Phase

| Phase | 覆盖范围 |
|-------|----------|
| **Web** | Web 漏洞利用、注入、SSRF、XSS、CSRF、反序列化 |
| **AD** | Active Directory 枚举、Kerberoasting、委派、域信任 |
| **Post-Exploitation** | 持久化、横向移动、提权、数据窃取 |
| **Reverse Engineering** | 二进制分析、协议逆向、固件提取 |
| **Code Audit** | 静态分析、漏洞发现、补丁对比 |
| **Payload** | 生成、编码、混淆、分级投递 |
| **Evasion** | EDR/AV 绕过、日志篡改、指标清除 |

### 扩展 Router/Pack 系列

| 领域 | 详细 Pack |
|------|-----------|
| **Recon** | OSINT、网络发现、服务枚举 |
| **API** | REST/GraphQL Fuzz、认证绕过、限速规避 |
| **Auth** | OAuth、JWT、SAML、Kerberos、NTLM 攻击面 |
| **Injection** | SQL、LDAP、XPath、模板、命令注入变体 |
| **File** | 上传攻击、路径穿越、LFI/RFI、文件解析漏洞 |
| **Business Logic** | 工作流滥用、竞态条件、权限边界违规 |
| **Cloud** | AWS/Azure/GCP IAM、Serverless、存储、元数据服务 |
| **Container / Kubernetes** | 容器逃逸、Pod 横向移动、供应链、RBAC 配置错误 |
| **Network / Protocol** | MITM、ARP/DNS 投毒、BGP 劫持、协议 Fuzz |
| **Crypto** | 弱密码套件、Padding Oracle、Nonce 重用、侧信道 |
| **Mobile** | APK/IPA 分析、证书固定绕过、Deep Link 滥用 |

## 安装

### 安装命令

```bash
python scripts/install.py
```

### 选项

| 参数 | 说明 |
|------|------|
| `--codex-home PATH` | 自定义 Codex 主目录（默认：`~/.codex`） |
| `--agents-home PATH` | 自定义 agents 目录（默认：`~/.agents`） |
| `--dry-run` | 预览模式，打印所有操作但不实际写入 |
| `--uninstall` | 卸载，移除所有托管文件、hooks 和 AGENTS.md 块 |

```bash
# 预览安装（不写入）
python scripts/install.py --dry-run

# 安装到自定义位置
python scripts/install.py --codex-home /opt/codex/home

# 完整卸载
python scripts/install.py --uninstall
```

### 安装器做了什么

1. **升级清理** — 读取上次安装的 manifest（`~/.codex/redteam-install-manifest.json`），移除所有旧版本托管路径，外加已知历史残留（`legacy-redteam-hook.py`、`red-team-command-doctrine-old`）
2. **核心文件** — 复制 `instruction.ctf.md` 和 `config.toml` 到 `~/.codex/`
3. **Hooks** — 部署 `session-start-context.py`、`hook-security-context-hook.py`、`redteam_state.py`、`core/` 到 `~/.codex/hooks/`
4. **子系统** — 部署 `router/`、`orchestrator/`、`automation/`、`session_patcher/` 到 `~/.codex/`
5. **技能包** — 部署全部 34 个 SKILL.md 领域卡从 `agents/skills/` 到 `~/.agents/skills/`（每个 skill 目录仅复制 SKILL.md）
6. **Seed prompts** — 复制 prompt 文件到 `~/.codex/prompts/`（已有文件跳过不覆盖）
7. **合并 hooks.json** — 清除旧的托管 hooks，注入当前版本的 `SessionStart` 和 `UserPromptSubmit` hooks（保留用户自定义 hooks）
8. **合并 AGENTS.md** — 在 `~/.codex/AGENTS.md` 中注入或更新托管块（`<!-- codex-redteam-optin-mode:start -->`），块外用户内容不受影响
9. **写 manifest** — 将所有托管路径记录到 `~/.codex/redteam-install-manifest.json`，供后续升级/卸载追踪
10. **验证** — 运行 `scripts/validate.py` 逐项检查各子系统文件是否就位

### 升级与幂等性

安装器是**幂等**的——多次运行不会重复注入 hooks 或 AGENTS.md 块。

每次运行时，先读取旧版本 manifest，仅移除本项目托管的旧安装文件，再从当前版本重新部署。这意味着：
- 版本升级干净，同时不触碰用户自己的文件
- `copy_tree` 整目录替换托管目录（`router/`、`orchestrator/` 等），skill 目录仅复制 `SKILL.md`
- `AGENTS.md` 和 `hooks.json` 从不直接删除——使用托管块合并逻辑，用户自定义内容不受影响
- 不会把 Python 缓存文件（`__pycache__`、`.pyc`、`.pyo`）复制到安装后的运行时目录
- 如果 manifest 丢失，安装器回退到清理当前目标集合 + 已知历史残留路径

```bash
# 重复执行安全——每次结果一致
python scripts/install.py
python scripts/install.py   # 第二次运行：清理 → 重新部署 → 同样的状态
```

## 快速开始

### 开启红队模式

```text
进入红队模式
开启红队模式
/redteam on
/redteam light
/redteam full
enable red team mode
```

### 关闭红队模式

```text
退出红队模式
关闭红队模式
/redteam off
disable red team mode
```

### 模式说明

| 模式 | 默认 | 适用场景 |
|------|------|----------|
| `normal` | 是 | 编码、文档、通用研究 |
| `redteam-light` | 否 | 定向安全分析、规划、审查 |
| `redteam-full` | 否 | 受限的红队工作流、实战操作 |

## 工作流程

红队模式开启后，运行时按以下主线工作：

```
phase → router → pack → leaf
```

1. **Phase 检测** — 规则优先匹配任务意图；模糊任务由语义判断兜底
2. **Router** — 将 phase 映射到对应的 detail pack 系列
3. **Pack** — 加载匹配领域的紧凑、可测试的技能包
4. **Leaf** — 执行具体技能或技术

`method` 仅作为**软提示**——可能在技术选择时提供参考，但不是主路由轴。

### 5-Phase 引擎 (v1.0.0)

Controller 通过结构化 pipeline 编排工作：

```
intent → phase routing → SKILL.md → taskbook → loop decision
```

- **SKILL.md 领域卡** — 每个领域通过纯 Markdown 的 `SKILL.md` 声明范围和退出条件。包含四个标准节：`## Domain`（领域和适用场景）、`## Boundaries`（禁止操作列表）、`## Pivot Hints`（转向建议）、`## Exit Evidence`（退出证据要求，含 required artifacts 和 minimum attempts）。
- **分级反馈门** — 四级 gate 判定：`pass`（推进）、`soft_fail`（重试/微调）、`pivot`（换路径）、`blocked`（停止等待人工）。
- **Loop Engine** — `decide_loop_action()` 输出五种决策之一：advance / verify / pivot / blocked / continue。
- **Phase Drive** — 编排更高层级工作流：recon → strategy → testing → reporting。

全程贯彻证据优先推理：证明一条路径后再扩展，区分事实与假设，以一条具体的下一步结束。

## Loop Runtime

Loop Runtime 按 `Observe -> Decide -> Act -> Verify -> Record -> Next` 运转。每次 loop 决策都必须包含：

- `trigger`：为什么启动当前闭环或改变方向
- `feedback_gate`：用哪个反馈门判断当前步骤是否有效
- `exit_condition`：什么条件下推进、换路、阻塞、报告或刷新上下文

当前实现包含 decision tree 路径选择、节奏分类、artifact/tool/scope gates、失败重试、quick card 刷新、JSONL decision log，以及 executor adapter 层。进入红队模式后，需要在 config.toml 中显式设置 `mode = "active"` / `"auto"` / `"assisted"` 才会进入 active executor；无配置时默认 `plan-only`（只规划不执行）。真实工具执行必须通过 Tool Registry、Scope Gate、Execution Gate 和已注册 Executor adapter。

## 自动化工具策略

自动化层不会把工具写死为唯一工具池。每次规划工具调用前，先读取用户本地可用 MCP/工具清单，再根据当前任务推导所需能力：

1. **优先使用 5 类实战工具能力：**
   - `WebFetch` — 内容获取、页面分析
   - `Browser MCP` — 浏览器自动化、真实交互、页面引擎
   - `IDA MCP` — 二进制逆向、协议分析
   - `JADX MCP` — APK 反编译、API 提取
   - `Current AI Agent` — 使用用户当前运行的 AI agent 进行代码生成和 AI 辅助分析
2. 如果首选工具不存在，则查找本地同等能力 MCP/工具替代。
3. 在计划或运行日志中记录 `preferred_tool`、`selected_tool`、`capability_match`、`risk`、`fallback_reason`。
4. 实际执行必须经过 Tool Registry → Scope Gate → Executor，不能让模型自由拼 shell 绕过工具层。
5. 进入红队模式后默认 plan-only；需在 config.toml 显式配置 `mode = "active"` 并接入 scoped adapter 通过 gate 后才进入实际执行。
6. 缺少必需工具、scope 或 adapter 时，必须明确 blocked / pivot，不能伪装成已经执行。
7. adapter 成功输出必须保存为 artifact，并重新通过 gate 后才能推进。

## 验证

```bash
# 完整测试套件
python -m unittest discover -s tests -p "test_*.py"

# 快速验证
python scripts/validate.py
```

验证覆盖：
- 安装器完整性检查
- 所有 phase/pack 组合的路由正确性
- 模式切换（normal ↔ light ↔ full ↔ off）
- SKILL.md 领域卡加载及全部 34 个 skill 的 Exit Evidence 验证
- 5-Phase 引擎：controller、verify engine、loop engine、taskbook
- Loop runtime 检查：decision tree、scope gate、adapter 执行、retry、artifact 保存、report gate
- 编排 gate 检查（scope、report、artifact）
- Prompt-chain 验证

## 已知局限

- 这是一个**运行时/配置层**，不是完整的攻击平台——提供路由、上下文管理、adapter-based 自动化和证据 gate，不提供硬编码 exploit 代码
- 工具可用性取决于用户本地的 MCP/工具清单
- 进入红队模式后自动化层会默认自动运行；实际执行深度取决于本地可用 MCP/工具、scope 和已注册 scoped adapter，缺少工具、scope 或 adapter 时会明确 blocked / pivot
- 红队模式需要每 session 显式开启
- 语义 phase 检测是 fallback——对定义明确的任务类型，规则匹配更可靠

## 免责声明

本项目**仅用于授权的渗透测试、红队研究和防御性安全实验**。用户在对任何非自有系统进行测试前，必须获得适当授权。作者对未经授权或非法使用不承担任何责任。

## 贡献与致谢

### 个人贡献者

- **Mingxi / 洺熙** — 建议添加语义判断作为 phase 检测 fallback；提议去除 methodology 层并细分 skills 以提升 AI 行为智能度
- **Nirvana** — 提出工作流优化方案及 overlay 安装启用
- **PINGS** — 提供 prompt-chain 鲁棒性审查

### 参考项目

方法层、路由层和 skill pack 结构借鉴自：

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)

## 贡献

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT](./LICENSE)

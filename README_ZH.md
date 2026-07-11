# Codex 红队 Opt-In 模式

[English](./README.md)

**当前版本：** v1.1.7

> 结构化红队路由默认关闭，必须显式开启；`instruction.ctf.md` 基础安全研究 profile 在所有模式下始终生效。

一个轻量级、证据驱动的红队运行时/配置层，用于 Codex。normal 模式保留 `instruction.ctf.md` 基础 profile，但不注入额外 prepoison、结构化 `phase -> router -> pack -> leaf` 路由和自动化循环；用户显式开启红队模式后，才启用这些额外运行时层。

## 项目初衷

AI 辅助安全工作中有两个常见陷阱：

1. **结构化路由意外启用** — 未经过显式模式命令就启用 phase、pack、自动化或 refusal-backstop 上下文。
2. **上下文膨胀** — 大量注入攻击方法论增加了 token 消耗，却没有真正提升路由质量。

本项目让结构化运行时保持 opt-in：normal 模式保留 `instruction.ctf.md` 基础 profile，但不注入额外 prepoison、refusal-backstop、phase、pack 或自动化上下文。显式开启后，通过 SKILL.md Loop Runtime 领域卡声明领域范围、边界约束和退出证据要求，由 5-Phase 引擎按证据驱动推进。

## 核心特性

- **三种显式模式**：`normal`（默认）、`redteam-light`（定向分析/规划）、`redteam-full`（受限的红队工作流）
- **结构化 JSON 运行状态**，session 隔离的状态文件
- **规则优先的 phase 检测**，语义判断作为模糊任务的 fallback
- **Pack-first 路由主线**：`phase → router → pack → leaf` — method 仅作为软提示，不是主路由轴
- **专用路由层** — 基于正则的路由引擎（中英文模式匹配），按领域细分的子路由器（5 个 Web、4 个 AD、6 个 Crypto、5 个 Network、3 个 Mobile），外部技能适配器（ACS/hackskills/qiushi）；路由层重构覆盖全部 13 个 phase，32 条 router→pack 映射
- **SKILL.md Loop Runtime 领域卡** — 纯 Markdown `scope-not-instruct` 模式：每张卡片通过 `## Domain`（领域声明）、`## Boundaries`（禁止操作）、`## Pivot Hints`（转向提示）、`## Exit Evidence`（退出证据）四节定义 AI 在哪个领域工作、什么不能做、什么条件下退出，不规定具体做法
- **5-Phase 引擎** — `controller.py` 编排 intent → phase routing → SKILL.md → taskbook → loop decision 全流程；分级反馈门（pass / soft_fail / pivot / blocked）驱动推进；`phase_drive` 实现 recon → strategy → testing → reporting 四阶段工作流
- **证据 Artifact 追踪** — 类型化、可验证的 `EvidenceArtifact` 对象（`enumeration`、`reproduction`、`impact`），驱动 gate 式推进
- **轻量 hooks** — 激活引擎、上下文预处理、意图引擎、循环引擎、phase 检测、语义 fallback、状态管理、拒答回退、严格 Codex wire 输出和 resume-safe 会话状态
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

需要 Python 3.11+，并安装 `requirements.txt` 中的依赖。安装器使用 `tomlkit` 对 `config.toml` 做 round-trip 合并。

```bash
python -m pip install -r requirements.txt
```

```bash
python scripts/install.py
```

### 选项

| 参数 | 说明 |
|------|------|
| `--project-home PATH` | 项目级安装根目录。Codex 文件写入 `PATH/.codex`，skills 默认写入 `PATH/.agents/skills`，项目级指导写入 `PATH/AGENTS.md` |
| `--agents-home PATH` | skill 安装目标目录（默认：`~/.agents`，使用 `--project-home` 时默认：`PATH/.agents`）。自定义运行时目录还需同时使用 `--enable-custom-skill-dirs` |
| `--codex-home PATH` | 自定义 Codex Home/profile 文件的安装目标（默认：`~/.codex`）。`PATH/AGENTS.md` 会作为该 Codex Home 的全局 guidance；项目级 guidance 请使用 `--project-home`。不要和 `--project-home` 混用 |
| `--log-root PATH` | 自定义自动化日志根目录，并写入安装 manifest |
| `--enable-custom-skill-dirs` | 让运行时优先使用 manifest 中记录的自定义 skill 目录 |
| `--dry-run` | 预览模式，打印所有操作但不实际写入 |
| `--uninstall` | 卸载，移除所有托管文件、hooks 和 AGENTS.md 块 |

```bash
# 预览安装（不写入）
python scripts/install.py --dry-run

# 安装到自定义 Codex Home/profile
python scripts/install.py --codex-home /opt/codex/home

# 项目级安装，包含项目根目录 AGENTS.md
python scripts/install.py --project-home /path/to/project

# 项目级安装，并把 skills 放到共享 agents 目录
python scripts/install.py --project-home /path/to/project --agents-home /path/to/agents --enable-custom-skill-dirs

# 项目级安装，自定义运行时日志目录
python scripts/install.py --project-home /path/to/project --log-root /path/to/logs

# 完整卸载
python scripts/install.py --uninstall

# 卸载使用了共享 skills 目录的项目级安装
python scripts/install.py --project-home /path/to/project --agents-home /path/to/agents --uninstall
```

项目级安装请使用 `--project-home /path/to/project`。不要用 `--codex-home /path/to/project/.codex` 代替它：这样会安装成 Codex Home/profile，`AGENTS.md` 会被 Codex 视为该 profile 的全局 guidance，而不是项目根目录 guidance。

`--agents-home` 只决定 skill 卡安装到哪里。指向自定义共享目录时，请同时添加 `--enable-custom-skill-dirs`，让运行时优先使用该目录。升级或卸载时应重复原安装使用的 `--project-home`、`--codex-home` 和 `--agents-home` 范围；如果已有托管路径超出当前范围，清理会在修改任何文件前停止。

### 运行时状态位置

红队会话状态和 memory 不写入安装 manifest，也不跟随项目目录保存。运行时只使用：

```text
$CODEX_HOME/redteam-mode/state/sessions/<session_id>.json
$CODEX_HOME/redteam-mode/state/memory/<session_id>.json
```

未设置 `CODEX_HOME` 时，上述 `$CODEX_HOME` 表示 `~/.codex`。安装器参数 `--codex-home` 只决定文件安装位置；使用自定义安装目录时，建议以相同环境变量启动 Codex：

```bash
CODEX_HOME=/opt/codex/home codex
```

不设置匹配的环境变量也可以运行，但状态会回退到 `~/.codex`。状态文件以 Codex session ID 命名，正常情况下不同会话不会发生冲突。

`--project-home` 不会让运行时状态变成项目本地状态。项目级安装同样使用当前 `CODEX_HOME`，未设置时使用 `~/.codex`。同一个 `CODEX_HOME` 下的不同 Codex config profile 共享状态根目录，但仍按 session ID 隔离。

卸载只移除托管的项目/plugin 文件，不会自动删除会话状态和 memory。如需手动清理，请确认当前 Codex Home 后删除对应目录：

```text
$CODEX_HOME/redteam-mode/state
~/.codex/redteam-mode/state
```

### 安装器做了什么

1. **配置预检** — 在复制或清理任何文件前，先解析并规划 `config.toml` 与 `hooks.json` 合并；已有配置非法时，安装会失败且不留下部分安装痕迹
2. **升级清理** — 同时读取正式 manifest 和 pending install transaction，先检查两者目标并集是否属于当前清理范围，再移除旧版本、未完成安装目标及已知历史残留
3. **核心文件** — 复制 `instruction.ctf.md`，并将 `config.toml` 合并到选定的 Codex Home（`~/.codex/`、自定义 `--codex-home` 或 `<project>/.codex/`）
4. **Hooks** — 部署 `session-start-context.py`、`hook-security-context-hook.py`、`redteam_state.py`、`core/` 到选定 Codex Home 的 `hooks/`
5. **子系统** — 部署 `router/`、`orchestrator/`、`automation/`、`session_patcher/` 到选定 Codex Home
6. **技能包** — 部署全部 35 个 SKILL.md 领域卡从 `agents/skills/` 到选定的 agents 目录（每个 skill 目录仅复制 SKILL.md）
7. **Seed prompts** — 复制 prompt 文件到选定 Codex Home 的 `prompts/` 目录（已有文件跳过不覆盖）
8. **合并 hooks.json** — 清除旧的托管 hooks，注入当前版本的 `SessionStart` 和 `UserPromptSubmit` hooks（保留用户自定义 hooks）
9. **合并 AGENTS.md** — 在选定 Codex Home 的 `AGENTS.md` 中注入或更新托管块，作为全局 guidance；使用 `--project-home` 时写入 `<project>/AGENTS.md`，作为项目级 guidance（`<!-- codex-redteam-optin-mode:start -->`），块外用户内容不受影响
10. **验证候选安装** — 使用候选 manifest 运行 `scripts/validate.py`，检查已部署文件、各子系统以及 skill 的安装目录和运行时实际选择目录
11. **提交 manifest** — 仅在验证成功后原子替换 `redteam-install-manifest.json` 并删除 pending transaction；部署或验证失败时保留 previous/candidate 目标供重试或卸载恢复

### 升级与幂等性

安装器是**幂等**的——多次运行不会重复注入 hooks 或 AGENTS.md 块。

每次运行时，先读取旧版本 manifest，仅移除本项目托管的旧安装文件，再从当前版本重新部署。这意味着：
- 版本升级干净，同时不触碰用户自己的文件
- `config.toml` 使用合并而不是覆盖；已有用户配置会保留，实际修改已有配置前会创建 `config.toml.YYYYMMDDHHMMSS.bak` 备份
- `config.toml` 合并使用 `tomlkit`，避免 `[[skills.config]]` 等数组表吞入本应属于 `[automation]` 的键
- manifest 会记录安装器新增的每个 `config.toml` 值和表；卸载会先移除仍保持原值的安装器托管项，再删除被引用文件，用户修改过的值会保留
- 对于没有字段所有权元数据的旧 manifest，如果 `config.toml` 仍引用 `instruction.ctf.md`，卸载会保留该文件，避免卸载后 Codex 配置失效
- 已有 `config.toml`、`hooks.json`、安装 manifest 或 pending transaction 非法时会在预检阶段失败，不会复制新文件，也不会清理旧路径；安装器与验证器均一致支持带 UTF-8 BOM 的 config 与 hooks
- POSIX hooks 使用安全的 shell 参数拼接，Windows hooks 使用编码后的 PowerShell 命令，因此 Python 或 Codex Home 路径中的空格、Unicode、引号和 `cmd.exe` 元字符不会被重新解释
- 升级会在清理前写入 pending transaction；重试和卸载会处理 previous/candidate 目标并集，验证成功后才原子提交正式 manifest 并移除事务
- GitHub Actions 使用 Python 3.11 在 Windows、Ubuntu 和 macOS 上运行完整测试套件
- 升级或卸载时，如果仍存在的托管路径超出当前清理范围，会在修改任何文件前终止并保留 manifest，用户可使用原始路径参数重试
- 自定义 `--agents-home` 未启用运行时优先级时安装器会给出警告；验证器会报告运行时 skill 根目录是否与安装目录一致
- `SessionStart` 和 `UserPromptSubmit` 只输出 Codex schema 支持的 wire 字段；路由 phase 保留在 `additionalContext` 中，不再作为未知字段序列化
- `SessionStart(source=resume|compact)` 保留已有会话模式，`startup` 与 `clear` 则重置为 normal
- 启用红队模式以及 `SessionStart(source=resume|compact)` 时会直接注入完整的 `Reverse.md` 补充上下文；normal startup 不注入这一模式级 overlay
- hook stdout 使用 ASCII-safe JSON，避免 Windows 传统代码页破坏 UTF-8 JSON 协议或中文上下文
- 相对安装参数以安装命令的工作目录为基准解析，生成的 hooks 和 manifest 字段均使用绝对路径
- `copy_tree` 整目录替换托管目录（`router/`、`orchestrator/` 等），skill 目录仅复制 `SKILL.md`
- `AGENTS.md`、`hooks.json` 和 `config.toml` 不会被升级清理删除——使用合并逻辑，用户自定义内容不受影响
- 项目级安装会将 managed AGENTS block 放在 `<project>/AGENTS.md`；旧的 `<project>/.codex/AGENTS.md` managed block 会安全迁移
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

模式命令应单独提交。启用 `redteam-light` 或 `redteam-full` 时会注入一次共享 prepoison 和 `Reverse.md` 补充上下文；之后每个真实任务 prompt 都会独立执行 `phase -> router -> pack -> leaf` 路由。处于红队模式的会话在 `resume` 或 `compact` 时会再次注入同一补充上下文。

### 关闭红队模式

```text
退出红队模式
关闭红队模式
/redteam off
disable red team mode
```

关闭模式会停止后续结构化路由，并将当前 session 状态文件重置为 normal，但不会删除该文件。`instruction.ctf.md` 基础 profile 和当前任务的历史上下文仍然有效；使用 `/clear` 或新建任务可移除之前的会话级上下文。

### 模式说明

| 模式 | 默认 | 适用场景 |
|------|------|----------|
| `normal` | 是 | `instruction.ctf.md` 基础 profile 生效；额外 prepoison、结构化路由、backstop 和自动化关闭 |
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
# 安装测试依赖
python -m pip install -r requirements-dev.txt

# 完整测试套件
python -m pytest -q

# 快速验证
python scripts/validate.py
```

验证覆盖：
- 安装器完整性检查
- 所有 phase/pack 组合的路由正确性
- 模式切换（normal ↔ light ↔ full ↔ off）
- SKILL.md 领域卡加载及全部 35 个 skill 的 Exit Evidence 验证
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

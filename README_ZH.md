# Codex 红队 Opt-In 模式

[English](./README.md)

**当前版本：** v1.3.0

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
- **模型感知提示词切换** — 从 hook payload、会话 `turn_context`、环境变量或 `config.toml` 获取实际模型；模型变化时自动注入对应破甲 profile
- **规则优先的 phase 检测**，语义判断作为模糊任务的 fallback
- **Pack-first 路由主线**：`phase → router → pack → leaf` — method 仅作为软提示，不是主路由轴
- **专用路由层** — 基于正则的路由引擎（中英文模式匹配），按领域细分的子路由器（5 个 Web、4 个 AD、6 个 Crypto、5 个 Network、3 个 Mobile），外部技能适配器（ACS/hackskills/qiushi）；路由层覆盖全部 14 个 phase，包含专用 jailbreak router→pack 映射
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
| `--model MODEL` | 为本次安装选择对应模型的系统提示词 profile；优先级高于环境变量和配置检测 |
| `--log-root PATH` | 自定义自动化日志根目录，并写入安装 manifest |
| `--enable-custom-skill-dirs` | 让运行时优先使用 manifest 中记录的自定义 skill 目录 |
| `--dry-run` | 预览模式，打印所有操作但不实际写入 |
| `--uninstall` | 卸载，移除所有托管文件、hooks 和 AGENTS.md 块 |

```bash
# 预览安装（不写入）
python scripts/install.py --dry-run

# 安装到自定义 Codex Home/profile
python scripts/install.py --codex-home /opt/codex/home

# 显式生成 GPT-5.6 对应的系统提示词
python scripts/install.py --model gpt-5.6-codex

# 安装后启动新会话：自动按本次 --model 选择系统提示词
%CODEX_HOME%\redteam-mode\codex-redteam.cmd --model gpt-5.6-sol

# macOS / Linux
$CODEX_HOME/redteam-mode/codex-redteam --model gpt-5.6-sol

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

模式命令和 OPSEC 命令应单独提交，整条 prompt 只能包含命令本身，允许首尾空白。引用、否定句、代码示例、命令后缀和包含多条命令的文本不会改变会话状态。启用 `redteam-light` 或 `redteam-full` 时会注入一次共享 prepoison 和 `Reverse.md` 补充上下文；之后每个真实任务 prompt 都会独立执行 `phase -> router -> pack -> leaf` 路由。处于红队模式的会话在 `resume` 或 `compact` 时会再次注入同一补充上下文。

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

### 新会话自动选择系统提示词

安装器按以下优先级识别模型：`--model` → `CODEX_MODEL` → 目标 `config.toml` → 上次安装 manifest → 源项目 `config.toml` → default。随后严格按以下顺序生成一个系统层文件：

1. 用户原 `model_instructions_file` 内容（如有）
2. `instruction.ctf.md`
3. 模型路由规则和所有配置的 `Jailbreak.gpt-5.x.md`

安装后的 `config.toml` 会让 `model_instructions_file` 指向 `./redteam-mode/system-instructions.md`。该系统文件包含基础指令、模型路由规则以及所有配置的 GPT-5.x Profile。`SessionStart` 提供会话初始化 fallback selector；每个被允许提交的 `UserPromptSubmit` 根据最新 Hook `model` 字段提供一个本轮权威 selector。当前 selector 会使历史 selector 失效，只激活一个匹配的系统 Profile，其余 Profile 保持惰性。

#### Codex App

安装后直接打开 Codex App。静态 `model_instructions_file` 加载统一系统路由文件；`SessionStart` 初始化 Profile，每个 `UserPromptSubmit` 再依据当前模型刷新 selector。会话内切换模型后，下一次用户提示会自动选择新 Profile，不需要专门 Hook `/model`。首次安装或 Hook 内容更新后，需要在 Codex 的 Hook 管理界面信任已安装的上下文 Hook。

#### Codex CLI

普通 `codex` 会话同样使用系统路由文件。安装器还会默认部署但不强制使用 `redteam-mode/codex-redteam.cmd` 和 `redteam-mode/codex-redteam`。包装启动器要求通过 `--model`、`-m` 或 `-c model=...` 显式指定模型，拒绝冲突的模型声明，并通过本次进程专用的 `model_instructions_file` 只加载一个匹配 Profile。临时文件仅位于 `redteam-mode/state/system_instructions/`，正常退出后自动删除。该进程锁定到所选 Profile 模型族：`gpt-5.6-sol` 与 `gpt-5.6-codex` 等同族变体可以继续使用；切换到其他模型族后的下一次提示会被阻止，并返回中英双语处理说明。

##### 可选 Launcher 使用方法

正常使用时请运行安装器生成的包装脚本，不要直接调用 `launcher.py`：

- 全局或自定义 Codex Home：Windows 使用 `%CODEX_HOME%\redteam-mode\codex-redteam.cmd`，macOS/Linux 使用 `$CODEX_HOME/redteam-mode/codex-redteam`。未设置 `CODEX_HOME` 时，使用 `%USERPROFILE%\.codex` 或 `~/.codex`。
- 项目级安装：Windows 使用 `<project>\.codex\redteam-mode\codex-redteam.cmd`，macOS/Linux 使用 `<project>/.codex/redteam-mode/codex-redteam`。
- 直接执行 `python redteam-mode/launcher.py ...` 仅用于开发和调试。

可以使用以下任意一种 Codex 参数形式指定启动模型；其他 Codex 参数会原样传递：

```bash
# 长模型参数
$CODEX_HOME/redteam-mode/codex-redteam --model gpt-5.6-sol

# 短模型参数，并传递其他 Codex 参数
$CODEX_HOME/redteam-mode/codex-redteam -m gpt-5.6-codex --sandbox workspace-write

# config 覆盖形式
$CODEX_HOME/redteam-mode/codex-redteam -c model=gpt-5.6-sol --cd /path/to/project
```

Launcher 要求显式提供一个不存在冲突的模型值。未指定模型、同时声明不同模型，或者由调用方传入 `model_instructions_file` 时会拒绝启动，因为该配置由 Launcher 按进程管理。Launcher 会在 `$CODEX_HOME/redteam-mode/state/system_instructions/` 下生成只包含单一 Profile 的临时 system-instructions 文件，将其传给 Codex 子进程，并在进程正常退出后删除。

通过 Launcher 启动的进程会锁定 Profile 模型族。由同一配置模式匹配的模型变体仍然兼容，例如 `gpt-5.6*` 下的 `gpt-5.6-sol` 与 `gpt-5.6-codex`。如果通过 `/model` 切换到其他 Profile 模型族，下一次 `UserPromptSubmit` 会被阻止，因为进程的 system layer 无法安全替换；此时应切回原模型族，或使用新模型重新通过 Launcher 启动。

默认映射可在 `config.toml` 中覆盖：

```toml
[redteam.model_prompt_profiles]
"gpt-5.6*" = "Jailbreak.gpt-5.6.md"
"gpt-5.5*" = "Jailbreak.gpt-5.5.md"
"gpt-5.4*" = "Jailbreak.gpt-5.4.md"
default = "Jailbreak.default.md"
```

Profile 文件位于 `$CODEX_HOME/prompts/`。匹配采用模型名通配符；未匹配或专用文件缺失时回落到 `default`。App 和普通 CLI 使用静态系统 catalog 加每轮 Hook selector，切换模型族后会在下一次提示时生效。可选的 `codex-redteam` 启动器会在进程启动前选择单 Profile，若要使用其他 Profile 模型族则必须重新启动。

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

主动执行适配器必须显式配置为 Python 可调用对象。表键应与发现到的工具名称一致，值使用 `module:function` 语法：

```toml
[automation.adapters]
"WebFetch" = "my_codex_adapters:web_fetch"
```

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
- SKILL.md 领域卡加载及全部 36 个 skill 的 Exit Evidence 验证
- 模型识别、profile 热切换、session state 更新和 jailbreak 专用路由
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

越狱、方法层、路由层和 skill pack 结构借鉴自：

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
- [MDX-Tom/gpt-5.6-instruct](https://github.com/MDX-Tom/gpt-5.6-instruct)

## 贡献

详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT](./LICENSE)

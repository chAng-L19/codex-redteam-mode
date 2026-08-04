# Codex 红队 Opt-In 模式

[English](./README.md)

**当前版本：v2.1.0**

> 默认保持 normal 模式；只有显式开启红队模式后，才启动持久化操作运行时。系统层基础指令与当前模型 profile 在所有模式下保持加载。

一个面向 Codex App 与 Codex CLI 的、显式开启的持久化红队运行时。它把用户目标编译为带成功准则的 `GoalContract`，通过类型化 `WorkflowSpec` 和真实 MCP 工具执行任务，保存可验证证据，并只在 `TerminalJudge` 证明全部准则后进入成功终态。

## 使用须知

使用该项目前，您应完整阅读 [README](./README_ZH.md) 文件，以防在使用过程中出现问题。

### 模型与系统 Prompt

安装器通过 `model_instructions_file` 在系统层组合用户原有指令、`instruction.ctf.md` 与对应的 `Jailbreak.gpt-5.x.md`。Codex App 新任务由 Hook 读取当前模型并选择 profile；CLI wrapper 在进程启动前生成单 profile 系统文件并锁定模型族。

### 提问的智慧

1. 若对于 **README** 中的内容有疑问，您应提出 **ISSUE** ，并附上 **README** 中相对应的内容以寻求帮助，或在 **微信交流群** 中以同样的方式询问问题。

   Do:
   ```text
   [贴出README中的文字]，我在这里有疑问，如何/为什么/怎么做/是什么
   ```
   Don't:
   ```text
   为什么我打开之后和视频里的不一样啊？
   ```

2. 若对于项目的维护有建议或想法，您可以`提出ISSUE`、`提出Pull Requests` 或 `在QQ交流群中提出建议`。

   Do:
   ```text
   我在xxx方面有xxx建议[图片]，这里可以修改/添加/删除xxx
   ```
   Don't:
   ```text
   能不能加一下外挂/卡密破解的功能啊？
   ```
### QQ群请加
805865662

### 运行边界

运行时把任务目标视为外层已完成范围校验的操作资产或本地沙箱，不在模型内重复索要范围材料。不可逆文件覆盖和对外提交仍保留显式工程确认，以避免误操作。

## 项目初衷

Codex 能够调用多种安全工具，但长流程容易受到会话中断、工具差异、结果搬运和“工具返回成功即任务完成”等问题影响。本项目将目标、动作、证据、恢复和终态判定统一到一条持久化执行主线中：

```text
GoalContract
  -> WorkflowSpec
  -> Durable Scheduler
  -> ToolBroker
  -> SemanticVerifier
  -> EvidenceGraph
  -> TerminalJudge
```

v2.1.0 使用统一的 `generic-adaptive` 运行时，不再使用旧 `phase -> router -> pack -> leaf` 路由、正则领域路由、Markdown ExitGate 或第二套 Automation 状态机。领域名称只作为资产与技术标签，不再控制运行时分支。

## 核心特性

- **显式开启**：默认始终为 `normal`，红队 operation 仅在收到模式命令后启动。
- **统一自适应执行**：仅保留一套版本化 `generic-adaptive` 工作流；场景、资产和技术只作为目标元数据与动态假设，不再复制控制流。
- **双层 Prompt Rewrite**：默认 Hook 在本地生成无损 Research Brief；可选 loopback Proxy 在主模型请求前调用当前模型或自定义中转站完成真实改写。
- **真实工具协作**：通过 stdio 或 Streamable HTTP 发现 MCP 工具；Host 独占能力可按 output contract 自动执行并回灌，无需用户搬运结果。
- **持久化与批次自治**：SQLite WAL、事件、租约、幂等键和独立 run ID 支持中断恢复、并发保护、多目标批次和取消清理。
- **证据驱动终态**：只有经过语义验证且具备目标绑定、父证据血缘、复现、影响、覆盖和回滚证明的结果，才能满足 `TerminalJudge`。

## 安装

### 安装命令

在仓库根目录安装依赖，然后安装到当前用户的 Codex Home：

```bash
python -m pip install -r requirements.txt
python scripts/install.py
```

安装器会自动从环境变量、目标配置或已有 manifest 识别模型；通常无需传入 `--model`。

项目级安装：

```bash
python scripts/install.py --project-home PATH
```

自定义 Skill 与持久化 operation 目录：

```bash
python scripts/install.py --project-home PATH --agents-home AGENTS_PATH --enable-custom-skill-dirs --log-root OPERATION_PATH
```

### 选项

| 参数 | 说明 |
|---|---|
| `--codex-home PATH` | 安装到指定 Codex Home/profile；其 `AGENTS.md` 作为全局指导文件 |
| `--project-home PATH` | 安装到 `PATH/.codex` 和 `PATH/.agents`，并管理项目根目录的 `AGENTS.md`；不可与 `--codex-home` 同时使用 |
| `--agents-home PATH` | 指定 Skill 安装目录；自定义目录建议同时使用 `--enable-custom-skill-dirs` |
| `--enable-custom-skill-dirs` | 让运行时优先使用 manifest 记录的自定义 Skill 目录 |
| `--log-root PATH` | 指定 SQLite、事件和证据产物的持久化根目录 |
| `--model MODEL` | 可选：覆盖自动检测结果，显式指定安装时使用的系统层模型 profile |
| `--enable-rewrite-proxy` | 启用 App/CLI 共用的本地 Rewrite Proxy，并保存原 `model_provider` 供卸载恢复 |
| `--dry-run` | 只预览安装、升级或卸载操作，不写入文件 |
| `--uninstall` | 删除 manifest 管理的文件、Hook、配置值和 `AGENTS.md` 区块 |

```bash
# 先预览项目级安装
python scripts/install.py --project-home PATH --dry-run

# 卸载用户级安装
python scripts/install.py --uninstall

# 卸载项目级安装
python scripts/install.py --project-home PATH --uninstall
```

### 运行时状态位置

默认 operation 根目录为：

```text
$CODEX_HOME/redteam-mode/operations/
├── runtime.sqlite3
└── artifacts/<run-id>/*.json
```

Hook 会话状态保存在 `$CODEX_HOME/redteam-mode/state/sessions`。可通过 `--log-root OPERATION_PATH` 更改 operation 数据位置。普通状态响应最多内联 64 KiB 证据；更大的已验证 payload 通过 `redteam_evidence` 按需读取，单个证据上限为 4 MiB。

升级和卸载不会主动删除运行时 session、memory 与 operation 数据，便于恢复、审计或手工清理。

### 安装器做了什么

- 保留已有用户配置，并只管理安装器写入的字段和文件。
- 合并 `config.toml`、Hook、系统层模型 profile catalog、Runtime MCP server、工作流和唯一边界 Skill。
- 部署 `rewrite_proxy.py` 与跨平台启动脚本；仅在显式启用时把 `model_provider` 切到 loopback Provider。
- 使用 pending transaction 部署候选版本，完成运行时验证后才原子提交 manifest。
- 升级时清理旧版受管路径，并对越界路径、无效 manifest、TOML 或 Hook 配置执行预检。
- 卸载时只移除未被用户修改的受管内容，保留用户自定义配置、提示词、Hook 和 `AGENTS.md` 内容。

## 快速开始

1. 完成安装并重启 Codex App，或重新启动 Codex CLI。
2. 新建任务，单独输入 `/redteam on`、`/redteam light` 或 `/redteam full`。
3. 输入完整目标；Hook 会把目标编译为 `GoalContract`，单目标和多目标分别进入独立 operation。
4. `redteam_run` 自动启动或恢复运行，通过 `ToolBroker` 调用可用 MCP 工具。
5. Host Agent 独占工具会收到 `next_action_spec`、gate、exit condition 和 output contract，并自动把 observation 回灌 Runtime。
6. `TerminalJudge` 证明所有目标准则、证据血缘和清理状态后生成最终结果。
7. 输入 `/redteam off`、`退出红队模式` 或 `关闭红队模式` 返回 normal 模式。

### Prompt Rewrite

默认 `context` 模式不改变 Provider：仅在用户显式开启红队模式后，Hook 才按“动作优先于技术对象”解析 Prompt，将普通开发请求排除在红队派发之外，继承短追问上下文，并输出 Clause 哈希、taxonomy、risk level、证据要求与可复现验证方案。用户未要求时不强制输出修复方案。

需要真实前置改写时：

```bash
python scripts/install.py --enable-rewrite-proxy
```

请求链路为：

```text
Codex App/CLI
  -> 127.0.0.1 Rewrite Proxy
  -> Rewrite Provider（仅收到改写规则 + 当前原始 Prompt）
  -> 本地注入四条研究会话历史（仅当请求已包含 Hook 红队上下文）
  -> 原 Codex Provider（收到原请求结构以及替换后的用户 Prompt、系统指令和工具定义）
```

`provider = "inherit"` 与 `model = "inherit"` 默认继承原 Provider 和当前 Codex 模型。若使用单独中转站，只需在 `model_providers` 中增加 Provider，并修改 `[redteam.prompt_rewrite]` 的 `provider`、`model` 和 `api_key_env`。normal 模式请求原样透传；Relay 丢失 URL、IP、CVE、路径、CLI 参数、Clause、高风险标记、上下文集合或语义保真标志时，Proxy 自动使用本地确定性改写。卸载会恢复原 `model_provider`。

CLI 可选 wrapper 会为当前进程锁定一个模型族 profile：

```bash
codex-redteam --model gpt-5.6-sol
```

切换模型族时需要新建 App 任务或重新启动 wrapper，以重新加载 `model_instructions_file`。

### 模式说明

| 模式 | 默认 | 适用场景 |
|---|---:|---|
| `normal` | 是 | 普通编码、文档和研究任务；不启动红队 operation，也不注入 operation doctrine |
| `redteam-light` | 否 | 通过 `/redteam on` 或 `/redteam light` 显式启动持久化 Goal/Workflow 执行 |
| `redteam-full` | 否 | 显式完整模式标记；v2.1.0 与 light 共用同一 Runtime、证据规则和 TerminalJudge 终态门槛 |

## 验证

```bash
# 安装测试依赖
python -m pip install -r requirements-dev.txt

# 完整测试套件
python -m pytest -q

# 快速验证当前目录下的安装内容
python scripts/validate.py --codex-home .
```

安装器和测试覆盖：

- 启动 Runtime MCP server 并验证唯一 `generic-adaptive` 工作流。
- 验证 Responses/Chat Completions Rewrite Proxy、显式模式门控、普通开发透传、Relay 数据隔离、动作/风险保真、锚点保真和确定性回退。
- 验证配置合并、事务升级、App/CLI Hook、模型 profile 和卸载保护。
- 验证并发启动与恢复、租约、幂等结果、批次取消和清理状态。
- 拒绝伪终态、伪证据、错误目标绑定和缺少可信父节点的派生证据。
- 验证真实 stdio/Streamable HTTP MCP、Host Agent handoff、秘密脱敏和工作流漂移保护。

GitHub Actions 使用 Python 3.11 在 Windows、Ubuntu 和 macOS 上运行完整测试。

## 已知局限

- 实际执行能力取决于当前可发现的 MCP 工具或 Host Agent 工具；缺少能力时 operation 会保留 pending handoff 或 deferred action。
- 名称、描述和输入 schema 都不足以表达能力的 MCP 工具，需要在 `automation.tool_capabilities` 中显式声明。
- `redteam-light` 与 `redteam-full` 在 v2.1.0 中共用执行引擎和终态规则，模式标签本身不会选择不同工作流。
- Rewrite Proxy 是显式启用的 Provider 级能力；默认 `context` 模式仍保持红队模式门控和零常驻服务。
- 单个证据 payload 上限为 4 MiB；常规状态只内联 64 KiB，较大证据需要使用 `redteam_evidence` 获取。
- 新任务会重置为 normal；切换模型族需要新建任务或重新启动 wrapper。

## 贡献与致谢

### 个人贡献者

- **Mingxi / 洺熙** — 建议添加语义判断作为 phase 检测 fallback；提议移除 methodology 层并细分 Skills，以提升 Agent 行为质量。
- **Nirvana** — 提出工作流优化方案及 overlay 安装支持。
- **PINGS** — 提供 jailbreak 文本增强和 prompt-chain 鲁棒性改进。

### 参考项目

早期路由/Skill 设计及当前越狱参考了：

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
- [gpt-5.6-instruct](https://github.com/MDX-Tom/gpt-5.6-instruct)

## star 历史

<a href="https://www.star-history.com/?repos=chAng-L19%2Fcodex-redteam-mode&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=chAng-L19/codex-redteam-mode&type=date&theme=dark&legend=top-left&sealed_token=CKO8uuC9r4XaKg8t4S3lVosw8UEFEOEmUKhK1gspPwDXctFtdeVgYQ-aWPH8rWLhIDCaZUmPasrE5qceMhl1M-dDRmHrpHDJ1lg4ZYhqGWAqYv8mcUdVEQ" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=chAng-L19/codex-redteam-mode&type=date&legend=top-left&sealed_token=CKO8uuC9r4XaKg8t4S3lVosw8UEFEOEmUKhK1gspPwDXctFtdeVgYQ-aWPH8rWLhIDCaZUmPasrE5qceMhl1M-dDRmHrpHDJ1lg4ZYhqGWAqYv8mcUdVEQ" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=chAng-L19/codex-redteam-mode&type=date&legend=top-left&sealed_token=CKO8uuC9r4XaKg8t4S3lVosw8UEFEOEmUKhK1gspPwDXctFtdeVgYQ-aWPH8rWLhIDCaZUmPasrE5qceMhl1M-dDRmHrpHDJ1lg4ZYhqGWAqYv8mcUdVEQ" />
 </picture>
</a>

## 贡献

贡献流程、代码规范和提交要求详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT](./LICENSE)

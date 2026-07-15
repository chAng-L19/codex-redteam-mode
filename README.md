# Codex Red Team Opt-In Mode

[中文说明](./README_ZH.md)

**Current release:** v1.3.0

> Structured red-team routing is off by default and must be enabled explicitly. The base `instruction.ctf.md` security profile remains active in every mode.

A lightweight, evidence-driven red team runtime/configuration layer for Codex. In normal mode, the base `instruction.ctf.md` profile remains active while additional prepoison context, structured `phase -> router -> pack -> leaf` routing, and the automation loop stay off. Explicitly enabling red-team mode activates those additional runtime layers.

## Why This Project

Two common pitfalls in AI-assisted security work:

1. **Uncontrolled structured routing** — phase, pack, automation, or refusal-backstop context activates without an explicit mode command.
2. **Context bloat** — heavy injection of offensive doctrine increases token cost without improving routing quality.

This project keeps the structured runtime opt-in: normal mode retains the base `instruction.ctf.md` profile but does not inject additional prepoison, refusal-backstop, phase, pack, or automation context. When explicitly enabled, SKILL.md Loop Runtime domain cards declare scope, boundaries, and exit evidence, while the 5-Phase engine drives evidence-based progression.

## Core Features

- **Three explicit modes**: `normal` (default), `redteam-light` (targeted analysis/planning), `redteam-full` (constrained red team workflow)
- **Structured JSON runtime state** with session-isolated state files
- **Model-aware prompt switching** — resolves the active model from hook payload, session `turn_context`, environment, or `config.toml`, then injects the matching jailbreak profile when the model changes
- **Rule-first phase detection** with semantic fallback for ambiguous tasks
- **Pack-first routing mainline**: `phase → router → pack → leaf` — method is a soft hint, not the primary routing axis
- **SKILL.md Loop Runtime domain cards** — pure Markdown `scope-not-instruct` format: each card has `## Domain` (scope declaration), `## Boundaries` (forbidden actions), `## Pivot Hints` (direction changes), `## Exit Evidence` (required artifacts and minimum attempts) — no YAML, no JSON
- **Graded feedback gates** — four-level gate decisions: `pass` (advance), `soft_fail` (retry/adjust), `pivot` (change path), `blocked` (halt for human)
- **Dedicated routing layer** — regex-based router engine (Chinese + English patterns), fine-grained sub-routers per domain (5 web, 4 AD, 6 crypto, 5 network, 3 mobile), external skill adapters (ACS/hackskills/qiushi)
- **Lightweight hooks** — activation engine, context prepoison, intent engine, loop engine, phase detector, semantic fallback, state manager, refusal backstop, strict Codex wire output, and resume-safe session state
- **Session patcher** — two-tier refusal detector (strong phrases + weak openers in Chinese + English), JSONL session cleaner with auto-backup and optional AI-powered rewrite
- **Bounded Loop Runtime** — each decision exposes a trigger, feedback gate, and exit condition so the agent can adjust pace before advancing
- **Artifact/gate-based progression** — prove one path before expanding, distinguish facts from assumptions
- **Automation Loop Runtime** — reads local MCP/tool inventory, derives required capabilities, runs scoped registered adapters, saves artifacts, and feeds gate decisions
- **Tool preference model**: prefer 5 practical tool classes (WebFetch, Browser MCP, IDA MCP, JADX MCP, Current AI Agent), fall back to equivalent local tools when needed
- **Managed incremental installer** — Python-based, preserves existing AGENTS.md and hooks.json, injects only managed blocks, supports `--uninstall` and idempotent upgrades

## Coverage Scenarios

### Core Phases

| Phase | Coverage |
|-------|----------|
| **Web** | Web exploitation, injection, SSRF, XSS, CSRF, deserialization |
| **AD** | Active Directory enumeration, Kerberoasting, delegation, trusts |
| **Post-Exploitation** | Persistence, lateral movement, privilege escalation, data exfiltration |
| **Reverse Engineering** | Binary analysis, protocol reversing, firmware extraction |
| **Code Audit** | Static analysis, vulnerability discovery, patch diffing |
| **Payload** | Generation, encoding, obfuscation, staging |
| **Evasion** | EDR/AV bypass, log tampering, indicator removal |

### Extended Router/Pack Families

| Domain | Detail Pack |
|--------|-------------|
| **Recon** | OSINT, network discovery, service enumeration |
| **API** | REST/GraphQL fuzzing, auth bypass, rate-limit evasion |
| **Auth** | OAuth, JWT, SAML, Kerberos, NTLM attack surfaces |
| **Injection** | SQL, LDAP, XPath, template, command injection variants |
| **File** | Upload attacks, path traversal, LFI/RFI, file parsing bugs |
| **Business Logic** | Workflow abuse, race conditions, privilege boundary violations |
| **Cloud** | AWS/Azure/GCP IAM, serverless, storage, metadata services |
| **Container / Kubernetes** | Escape, pod lateral movement, supply chain, misconfigured RBAC |
| **Network / Protocol** | MITM, ARP/DNS poisoning, BGP hijack, protocol fuzzing |
| **Crypto** | Weak cipher suites, padding oracles, nonce reuse, side channels |
| **Mobile** | APK/IPA analysis, certificate pinning bypass, deep link abuse |

## Installation

### Python (cross-platform)

Requires Python 3.11+ and the dependencies in `requirements.txt`. The installer uses `tomlkit` for round-trip `config.toml` merging.

```bash
python -m pip install -r requirements.txt
```

```bash
python scripts/install.py
```

### Options

| Option | Description |
|--------|-------------|
| `--project-home PATH` | Project-level install root. Writes Codex files to `PATH/.codex`, skills to `PATH/.agents/skills` unless `--agents-home` is set, and project guidance to `PATH/AGENTS.md` |
| `--agents-home PATH` | Skill installation destination (default: `~/.agents`, or `PATH/.agents` with `--project-home`). For a custom runtime directory, also use `--enable-custom-skill-dirs` |
| `--codex-home PATH` | Custom installation target for Codex Home/profile files (default: `~/.codex`). Writes `PATH/AGENTS.md` as global guidance; use `--project-home` for project guidance. Do not combine with `--project-home` |
| `--model MODEL` | Select the model-specific system prompt profile for this installation; overrides environment and config detection |
| `--log-root PATH` | Custom automation log root recorded in the install manifest |
| `--enable-custom-skill-dirs` | Prioritize the manifest-recorded custom skill directory at runtime |
| `--dry-run` | Preview all operations without writing any files |
| `--uninstall` | Remove all managed files, hooks, and AGENTS.md blocks |

```bash
# Preview before install
python scripts/install.py --dry-run

# Custom Codex Home/profile install
python scripts/install.py --codex-home /opt/codex/home

# Explicitly compose the GPT-5.6 system instructions
python scripts/install.py --model gpt-5.6-codex

# Start a new session with automatic prompt selection from --model
%CODEX_HOME%\redteam-mode\codex-redteam.cmd --model gpt-5.6-sol

# macOS / Linux
$CODEX_HOME/redteam-mode/codex-redteam --model gpt-5.6-sol

# Project-level install, including project AGENTS.md
python scripts/install.py --project-home /path/to/project

# Project-level install with shared skills directory
python scripts/install.py --project-home /path/to/project --agents-home /path/to/agents --enable-custom-skill-dirs

# Project-level install with custom runtime log root
python scripts/install.py --project-home /path/to/project --log-root /path/to/logs

# Full uninstall
python scripts/install.py --uninstall

# Uninstall a project install that used a shared skills directory
python scripts/install.py --project-home /path/to/project --agents-home /path/to/agents --uninstall
```

Use `--project-home /path/to/project` for project-level installs. Do not use `--codex-home /path/to/project/.codex` as a substitute: that installs into a Codex Home/profile, so `AGENTS.md` is treated as global guidance for that profile rather than as project-root guidance.

`--agents-home` controls where skill cards are installed. When it points to a custom shared directory, add `--enable-custom-skill-dirs` to make the runtime prioritize that directory. Repeat the original `--project-home`, `--codex-home`, and `--agents-home` scope when upgrading or uninstalling; cleanup stops before changing files if existing managed paths fall outside the current scope.

### Runtime State Location

Red-team session state and memory are not stored in the install manifest or project directory. At runtime they use:

```text
$CODEX_HOME/redteam-mode/state/sessions/<session_id>.json
$CODEX_HOME/redteam-mode/state/memory/<session_id>.json
```

When `CODEX_HOME` is unset, `$CODEX_HOME` above means `~/.codex`. The `--codex-home` installer option only selects where files are installed; for a custom install, it is recommended to launch Codex with the same environment value:

```bash
CODEX_HOME=/opt/codex/home codex
```

Running without the matching environment variable is supported, but runtime state then falls back to `~/.codex`. State files are keyed by Codex session ID, so unrelated sessions are not expected to collide.

`--project-home` does not make runtime state project-local. Project installs also use the active `CODEX_HOME`, or `~/.codex` when it is unset. Different Codex config profiles under the same `CODEX_HOME` share this state root while remaining separated by session ID.

Uninstall removes managed project/plugin files but intentionally keeps session state and memory. If manual cleanup is desired, remove one of these roots after confirming the active Codex Home:

```text
$CODEX_HOME/redteam-mode/state
~/.codex/redteam-mode/state
```

```bash
# Safe to run repeatedly — same result each time
python scripts/install.py
python scripts/install.py   # second run: cleanup → fresh deploy → same state
```

## Quick Start

### Enable Red Team Mode

```text
进入红队模式
开启红队模式
/redteam on
/redteam light
/redteam full
enable red team mode
```

Submit mode and OPSEC commands as a separate prompt containing only the command; leading and trailing whitespace is allowed. Quoted commands, negations, code examples, command suffixes, and prompts containing multiple commands do not change session state. Enabling `redteam-light` or `redteam-full` injects the shared prepoison and `Reverse.md` supplemental context once; each subsequent task prompt is routed independently through `phase -> router -> pack -> leaf`. Active red-team sessions inject the same supplemental context again on `resume` or `compact`.

### Disable Red Team Mode

```text
退出红队模式
关闭红队模式
/redteam off
disable red team mode
```

Disabling the mode stops future structured routing and resets the current session state file to normal without deleting it. The base `instruction.ctf.md` profile and prior task context remain active; use `/clear` or start a new task to remove prior per-session context.

### Mode Reference

| Mode | Default | Use Case |
|------|---------|----------|
| `normal` | Yes | Base `instruction.ctf.md` profile active; additional prepoison, structured routing, backstop, and automation inactive |
| `redteam-light` | No | Targeted security analysis, planning, review |
| `redteam-full` | No | Constrained red team workflow, operations |

### Automatic New-Session System Prompt Selection

The installer resolves the model in this order: `--model` → `CODEX_MODEL` → target `config.toml` → previous install manifest → source `config.toml` → default. It then writes one system-layer file in this exact order:

1. Existing user `model_instructions_file` content, when configured
2. `instruction.ctf.md`
3. Model-routing rules and every configured `Jailbreak.gpt-5.x.md`

The installed `config.toml` points `model_instructions_file` to `./redteam-mode/system-instructions.md`. That system file contains the base instructions, model-routing rules, and every configured GPT-5.x profile. Every new conversation's `SessionStart` hook reports only the current model/profile metadata; the system-layer router activates exactly the matching section and treats all other profile sections as inert.

#### Codex App

After installation, open Codex App normally. When a new conversation selects GPT-5.5 or GPT-5.6 in the App, the static `model_instructions_file` loads the shared system router and `SessionStart` metadata selects the matching profile. After first install or a hook-content update, trust this `SessionStart` hook in Codex's hook manager. Start a new conversation when changing models; an existing conversation retains its startup system profile.

#### Codex CLI

Ordinary `codex` sessions also use the system router. The installer additionally deploys `redteam-mode/codex-redteam.cmd` and `redteam-mode/codex-redteam`. Before starting Codex, these launchers detect the model from `--model`, `-m`, or `-c model=...`, then `CODEX_MODEL` or `config.toml`, and load only the matching profile through a process-local `model_instructions_file` override. Each CLI session receives an independent `system-instructions.Jailbreak.gpt-5.x.SESSION.md`, removed after the process exits.

Override the default mapping in `config.toml`:

```toml
[redteam.model_prompt_profiles]
"gpt-5.6*" = "Jailbreak.gpt-5.6.md"
"gpt-5.5*" = "Jailbreak.gpt-5.5.md"
"gpt-5.4*" = "Jailbreak.gpt-5.4.md"
default = "Jailbreak.default.md"
```

Profile files live under `$CODEX_HOME/prompts/`. Model keys support glob patterns; an unmatched model or missing specialized file falls back to `default`. App and ordinary CLI sessions use the system catalog plus `SessionStart` metadata; the `codex-redteam` CLI launcher selects one profile before process startup. Both approaches use a new conversation as the model-switch boundary.

## Automation Tool Policy

Before planning tool use, the automation layer reads the user's local MCP/tool inventory, derives required capabilities, then selects tools in this order:

1. **Prefer these 5 practical tool classes:**
   - `WebFetch` — content fetch and page analysis
   - `Browser MCP` — browser automation and engine-backed interaction
   - `IDA MCP` — binary reverse engineering and protocol analysis
   - `JADX MCP` — APK decompilation and API extraction
   - `Current AI Agent` — code generation and AI-assisted analysis using the AI agent the user is currently running
2. If a preferred tool is unavailable, select an equivalent registered local MCP/tool.
3. Record `preferred_tool`, `selected_tool`, `capability_match`, `risk`, and `fallback_reason`.
4. Execute only through Tool Registry → Scope Gate → Executor.
5. In red-team mode, run active automation by default; execute only when a scoped adapter is registered and all gates pass.
6. If a required tool, scope, or adapter is missing, block or pivot explicitly instead of pretending execution happened.
7. Save successful adapter output as artifacts and re-check gates before advancing.

Active adapters are configured explicitly as Python callables. The table key must match the discovered tool name and the value uses `module:function` syntax:

```toml
[automation.adapters]
"WebFetch" = "my_codex_adapters:web_fetch"
```

## Validation

```bash
# Install test dependencies
python -m pip install -r requirements-dev.txt

# Full test suite
python -m pytest -q

# Quick validation
python scripts/validate.py
```

Validation covers:
- Installer integrity checks
- Routing correctness across all phase/pack combinations
- Mode switching (normal ↔ light ↔ full ↔ off)
- Loop runtime checks (decision tree, scope gate, adapter execution, retry, artifact saving, report gate)
- Orchestration gate checks (scope, report, artifact)
- Prompt-chain verification
- Model discovery, profile hot switching, session-state updates, and dedicated jailbreak routing

## Known Limitations

- This is a **runtime/configuration layer**, not a complete attack platform — it provides routing, context management, adapter-based automation, and evidence gates, not hardcoded exploit code
- Tool availability depends on the user's local MCP/tool inventory
- Real execution requires explicitly registered scoped adapters; missing tools, scope, or adapters are blocked or pivoted instead of being treated as successful execution
- Red-team mode must be explicitly enabled per session
- Semantic phase detection is a fallback — rule-first matching is more reliable for well-defined task types

## Disclaimer

This project is intended **solely for authorized penetration testing, red team research, and defensive security experiments**. Users must obtain proper authorization before testing any system they do not own. The authors disclaim all liability for unauthorized or illegal use.

## Contributions & Acknowledgements

### Individual Contributors

- **Mingxi / 洺熙** — suggested adding semantic judgment as fallback for phase detection; proposed removing methodology while subdividing skills for smarter AI behavior
- **Nirvana** — proposed workflow optimization with overlay installation enablement
- **PINGS** — offered prompt-chain robustness review

### Reference Projects

Jailbreak,Method layer, routing layer, and skill pack structure draw inspiration from:

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
- [MDX-Tom/gpt-5.6-instruct](https://github.com/MDX-Tom/gpt-5.6-instruct)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[MIT](./LICENSE)

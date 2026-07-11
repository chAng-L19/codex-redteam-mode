# Codex Red Team Opt-In Mode

[中文说明](./README_ZH.md)

**Current release:** v1.1.6

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
| `--log-root PATH` | Custom automation log root recorded in the install manifest |
| `--enable-custom-skill-dirs` | Prioritize the manifest-recorded custom skill directory at runtime |
| `--dry-run` | Preview all operations without writing any files |
| `--uninstall` | Remove all managed files, hooks, and AGENTS.md blocks |

```bash
# Preview before install
python scripts/install.py --dry-run

# Custom Codex Home/profile install
python scripts/install.py --codex-home /opt/codex/home

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

### What the Installer Does

1. **Configuration preflight** — parses and plans both `config.toml` and `hooks.json` merges before copying or cleaning any files, so invalid existing configuration leaves the install untouched
2. **Upgrade cleanup** — reads the manifest from the selected Codex Home (`<codex-home>/redteam-install-manifest.json`), preflights every existing managed path against the current cleanup scope, then removes old tracked paths plus known legacy remnants (`legacy-redteam-hook.py`, `red-team-command-doctrine-old`)
3. **Core files** — copies `instruction.ctf.md` and merges `config.toml` into the selected Codex Home (`~/.codex/`, custom `--codex-home`, or `<project>/.codex/`)
4. **Hooks** — deploys `session-start-context.py`, `hook-security-context-hook.py`, `redteam_state.py`, and `core/` to the selected Codex Home's `hooks/`
5. **Subsystems** — deploys `router/`, `orchestrator/`, `automation/`, and `session_patcher/` to the selected Codex Home
6. **Skill packs** — deploys all 35 SKILL.md domain cards from `agents/skills/` to the selected agents home (only `SKILL.md` is copied per skill directory)
7. **Seed prompts** — copies prompt files to the selected Codex Home's `prompts/` directory (skips existing)
8. **Merge hooks.json** — strips old managed hooks, then injects the current `SessionStart` and `UserPromptSubmit` hooks (preserves user-defined hooks)
9. **Merge AGENTS.md** — injects or updates a managed block (`<!-- codex-redteam-optin-mode:start -->`) into the selected Codex Home's `AGENTS.md` as global guidance, or `<project>/AGENTS.md` with `--project-home` as project guidance (preserves user content outside the block)
10. **Validate candidate** — runs `scripts/validate.py` against the deployed files and a candidate manifest, verifying every subsystem and the installed/runtime-selected skill roots
11. **Commit manifest** — atomically replaces `redteam-install-manifest.json` only after validation succeeds; the previous manifest remains available if deployment or validation fails

### Upgrade & Idempotency

The installer is **idempotent** — running it repeatedly is safe and will not duplicate hooks or AGENTS.md blocks.

On each run, it reads the previous manifest, removes only project-managed files from the old install, then re-deploys from the current version. This means:
- Version upgrades are clean without touching user-owned files
- `config.toml` is merged instead of overwritten; existing user settings are preserved, and changed existing configs are backed up as `config.toml.YYYYMMDDHHMMSS.bak`
- `config.toml` merging uses `tomlkit` so array tables such as `[[skills.config]]` do not receive keys meant for `[automation]`
- The manifest records each `config.toml` value and table added by the installer; uninstall removes only unchanged installer-owned values before deleting referenced files, while user-modified values are preserved
- Legacy manifests without field ownership metadata preserve `instruction.ctf.md` when `config.toml` still references it, avoiding a broken Codex profile after uninstall
- Invalid existing `config.toml`, `hooks.json`, or install manifests fail during preflight before files are copied or previous paths are cleaned; UTF-8 BOM-prefixed config and hooks files are accepted consistently by installation and validation
- Generated hooks contain separately quoted POSIX and Windows commands, so Python and custom Codex Home paths containing spaces execute correctly
- Upgrades retain the previous manifest during deployment, validate with a candidate manifest, and atomically replace it only after validation succeeds
- Upgrade and uninstall cleanup abort before changing files when an existing managed path is outside the current scope; the manifest is preserved so the operation can be retried with the original path arguments
- Custom `--agents-home` installs warn when runtime priority is not enabled, and validation reports when the runtime-selected skill root differs from the installed root
- `SessionStart` and `UserPromptSubmit` output only Codex-supported wire fields; route phase remains inside `additionalContext` instead of being serialized as an unknown field
- `SessionStart(source=resume|compact)` preserves the existing session mode, while `startup` and `clear` reset to normal
- Red-team activation and `SessionStart(source=resume|compact)` inject the complete `Reverse.md` supplemental context directly; normal startup remains free of this mode-level overlay
- Hook JSON is ASCII-safe on stdout, so Windows legacy code pages cannot corrupt the UTF-8 JSON protocol or Chinese context
- Relative install arguments are resolved against the install command's working directory, and generated hooks and manifest fields use absolute paths
- `copy_tree` replaces managed directories (`router/`, `orchestrator/`, etc.) wholesale; skill directories copy only `SKILL.md`
- `AGENTS.md`, `hooks.json`, and `config.toml` are never deleted by upgrade cleanup — they use merge logic so user customizations survive
- Project installs place the managed AGENTS block in `<project>/AGENTS.md`; old `<project>/.codex/AGENTS.md` managed blocks are migrated safely
- Python cache files (`__pycache__`, `.pyc`, `.pyo`) are not copied into the installed runtime
- If the manifest is missing, the installer falls back to cleaning the current target set plus known legacy paths

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

Submit mode commands as a separate prompt. Enabling `redteam-light` or `redteam-full` injects the shared prepoison and `Reverse.md` supplemental context once; each subsequent task prompt is routed independently through `phase -> router -> pack -> leaf`. Active red-team sessions inject the same supplemental context again on `resume` or `compact`.

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

## Working Flow

When red-team mode is enabled, the runtime follows this mainline:

```
phase → router → pack → leaf
```

1. **Phase detection** — rule-first matching against task intent; semantic fallback when ambiguous
2. **Router** — maps phase to the appropriate detail pack family
3. **Pack** — loads the compact, testable skill pack for the matched domain
4. **Leaf** — executes the concrete skill or technique

`method` is a **soft hint** — it may add value for technique selection but is not the primary routing axis.

Evidence-first reasoning is enforced throughout: prove one path before expanding, distinguish facts from assumptions, end with one concrete next step.

## Loop Runtime

The Loop Runtime follows `Observe -> Decide -> Act -> Verify -> Record -> Next`. Every loop decision carries:

- `trigger`: why this loop started or changed direction
- `feedback_gate`: the gate used to judge whether the current step is valid
- `exit_condition`: the condition for advancing, pivoting, blocking, reporting, or refreshing context

The runtime now includes decision-tree path selection, rhythm classification, artifact/tool/scope gates, retry handling, quick-card refreshes, JSONL decision recording, and an executor adapter layer. In red-team mode, automation requires explicit `mode = "active"` / `"auto"` / `"assisted"` in config.toml to enable active execution; without configuration it defaults to `plan-only`. Direct tool execution is intentionally bounded behind Tool Registry, Scope Gate, Execution Gate, and registered Executor adapters.

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

## Validation

```bash
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

Method layer, routing layer, and skill pack structure draw inspiration from:

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[MIT](./LICENSE)

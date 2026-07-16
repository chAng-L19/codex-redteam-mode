# Changelog

All notable changes to the Codex Red Team Opt-In Mode project.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Added an App-compatible system-layer profile catalog. A static `model_instructions_file` now contains all configured GPT-5.x profiles plus a strict router, while every new conversation emits selector-only model metadata from `SessionStart`.
- Added cross-platform `codex-redteam` launchers that detect the model before a new Codex process starts, generate a model-specific system instructions file, and pass it through a process-local `model_instructions_file` override.
- Added independent per-session system files so concurrent GPT-5.5 and GPT-5.6 sessions do not overwrite each other's system prompt; launchers remove their temporary profile after Codex exits.
- Added a `Stop` hook that records refusal detection from `last_assistant_message` and injects a one-time recovery overlay on the next active red-team prompt.

## [1.3.0] - 2026-07-14

### Added

- Added a managed GPT-5.4 jailbreak profile and the `gpt-5.4*` automatic model-profile mapping.
- Added normalized-content integrity coverage for the imported GPT-5.4 CTF Core Contract.
- Extended installer validation, deployment, uninstall, and model-selection regression coverage to GPT-5.4.
- Added `--model` plus config/environment/manifest model detection for selecting the installation-time system profile.

### Changed

- The installer now composes the user's existing system instructions, `instruction.ctf.md`, and the matching GPT-5.x jailbreak profile into `$CODEX_HOME/redteam-mode/system-instructions.md` and configures it through `model_instructions_file`.
- Model-profile hooks now emit selection metadata only; the jailbreak body is delivered exclusively through the generated model instructions file.
- Model changes take effect after reinstalling the profile and starting a new task instead of attempting same-task hot switching.

### Fixed

- Uninstall restores a replaced user `model_instructions_file` value while removing the generated system file and preserving the original user instruction file.

## [1.2.0] - 2026-07-14

### Added

- Added model-aware prompt profiles for GPT-5.6, GPT-5.5, and a generic fallback, selected from hook payload, transcript `turn_context`, environment, or Codex config.
- Added automatic prompt-profile reinjection when the active model changes and persisted the active model/profile in session state.
- Added a dedicated `jailbreak -> llm-prompt-injection -> redteam-jailbreak-detail-pack -> llm-prompt-injection` route.
- Added installer validation and regression coverage for profile selection, transcript discovery, live model switching, prompt deployment, and uninstall cleanup.

### Changed

- Integrated the GPT-5.6 unrestricted instruction as a managed model profile while keeping `instruction.ctf.md` as the canonical instruction file.
- Expanded the installed domain-card set from 35 to 36 and documented model-profile customization.

### Fixed

- Active automation can now load explicitly configured `module:function` adapters into the Hook controller's Executor.
- CVE candidates and automation artifacts now persist across controller turns instead of being dropped between state and memory representations.
- Windows hook commands now resolve an available PowerShell executable, including `pwsh`, and Python dependencies are version-pinned for reproducible installs and tests.

## [1.1.7] - 2026-07-11

### Fixed

- Runtime manifest discovery now checks the current Codex Home first, so custom `--codex-home` installs work even when hooks do not inherit `CODEX_HOME`.
- Installer `config.toml` merging now preflights TOML parsing before cleanup or file copies, preventing partial installs when an existing config is invalid.
- Installer paths are normalized to absolute paths before hook rendering, manifest writes, runtime lookup, or cleanup.
- Existing `hooks.json` files are BOM-tolerant and fully validated before install or uninstall changes begin, preventing partial operations on invalid hook configuration.
- Session backstop lookup now searches the transcript's complete session root, so the previous session can be found across date directories without crossing Codex profiles.
- Runtime and validation now accept UTF-8 BOM-prefixed `config.toml` files, preventing valid automation settings from silently falling back to `plan-only`.
- Upgrade and uninstall now preflight all existing managed paths against the current cleanup scope before changing files. Out-of-scope paths preserve the manifest and return a non-zero exit so the operation can be retried with the original `--agents-home`.
- Custom `--agents-home` installs now warn when `--enable-custom-skill-dirs` is missing, and validation reports both the installed and runtime-selected skill roots.
- `SessionStart` and `UserPromptSubmit` hook output now matches Codex's strict context-hook schema. Internal route phase is used for role overlays but is no longer serialized as an unsupported wire field.
- `SessionStart` now preserves the existing mode for `resume` and `compact` sources, while `startup`, `clear`, missing, and unknown sources reset safely to normal.
- Hook JSON output is now ASCII-safe, preventing Windows GBK/CP936 stdout encoding from corrupting the UTF-8 hook protocol or Chinese context.
- Installer manifests now record the exact `config.toml` values and tables added by the installer. Uninstall removes only unchanged installer-owned values before deleting `instruction.ctf.md`; legacy manifests preserve the file when configuration ownership cannot be proven.
- Red-team light/full activation and resumed or compacted red-team sessions now inject the complete `Reverse.md` supplemental context directly. Normal startup remains free of this mode-level overlay, and subsequent task prompts continue to use the existing per-turn `phase -> router -> pack -> leaf` routing.
- Normal `SessionStart` no longer injects the additional prepoison or refusal backstop. Light/full activation injects the existing prepoison once, resume/compact restores it only for active red-team sessions, and disabling the mode now accurately describes the base profile and retained task history.
- Session state now persists under `$CODEX_HOME/redteam-mode/state/sessions` (falling back to `~/.codex`) instead of `TEMP`/`TMP`; session memory uses the sibling `memory` directory, missing session IDs no longer create shared `global.json` state, and uninstall intentionally preserves these runtime files.
- Windows hook definitions now invoke Base64-encoded PowerShell commands, preventing spaces, Unicode, quotes, and `cmd.exe` metacharacters in Python or Codex Home paths from breaking `SessionStart` and `UserPromptSubmit`; POSIX hooks retain shell-safe argument joining.
- Existing manifests now fail closed when their JSON structure or managed paths are invalid, before any installation, cleanup, or uninstall changes occur.
- Upgrades now write a pending install transaction before cleanup. Failed deployment targets remain recoverable, while retry and uninstall reconcile the union of previous and candidate targets; successful validation atomically commits the formal manifest and removes the transaction.
- Installed `hooks.json` validation now uses BOM-tolerant UTF-8 decoding, matching installer behavior and the documented BOM support.
- Prompt files created by the installer are now recorded in the manifest and removed on uninstall, while pre-existing same-name user prompts remain unowned and preserved across reinstall and uninstall.

### Changed

- Added a GitHub Actions test matrix for Windows, Ubuntu, and macOS using Python 3.11, including platform-specific hook command execution with shell metacharacter paths.
- Clarified `--codex-home` as a Codex Home/profile-level install whose `AGENTS.md` is global guidance, while `--project-home` writes project-level `AGENTS.md`.
- Documented manifest lookup and upgrade cleanup as relative to the selected Codex Home instead of hard-coding `~/.codex`.
- Relative install arguments are resolved against the install command's working directory and stored as absolute paths.
- Installation examples now pair shared skill directories with `--enable-custom-skill-dirs` and show the matching uninstall scope.

## [1.0.0] - 2026-06-28

### Changed - Loop Runtime Redesign (P0-P7)

- **Architecture**: Replaced multi-knowledge-card system (YAML/JSON runtime cards + references/) with lightweight Loop Runtime. Each skill is now a single `SKILL.md` domain card following Observe -> Decide -> Act -> Verify -> Record -> Next flow.
- **SKILL.md format**: Unified domain card with sections: `## Domain`, `## Boundaries`, `## Pivot Hints`, `## Exit Evidence`. Replaces `skill_card.yaml`, `skill_card.json`, and `references/` directories.
- **Graded feedback gates**: Introduced four-level gate system (`pass` / `soft_fail` / `pivot` / `blocked`) replacing binary pass/fail.
- **skill_card.py**: Rewritten to parse only SKILL.md (Markdown-native, no YAML/JSON dependency).
- **install.py**: New `copy_skill_md()` function copies only SKILL.md per skill directory instead of entire directory trees. Version bumped to 1.0.0.
- **install.py**: Directory copy now excludes Python cache files (`__pycache__`, `.pyc`, `.pyo`) so overlay installs stay clean even if the source tree contains local caches.
- **34 skill directories**: All converted to Loop Runtime SKILL.md format. Legacy YAML/JSON runtime cards and references directories are removed from `agents/skills/`.
- **brain.py**: Rewritten to 5-phase framework (recon -> test -> hypothesis -> verify -> report) with `phase_drive` orchestrator and per-domain halt mechanism.
- **Tool modules**: 5-module upgrade: `recon_ports`, `recon_subdomains`, `recon_directories` (upgraded), `vuln_scanner`, `sqli_detector` (new).
- **README.md / README_ZH.md**: Updated to describe Loop Runtime SKILL.md architecture, graded gates, automatic red-team automation startup, and new installer behavior.
- **Documentation encoding**: Restored README, README_ZH, and CHANGELOG text to valid UTF-8 without changing prompt/refusal-direction scripts.
- **Automation startup**: Red-team sessions default to `plan-only` when no explicit `[automation].mode` is configured. Set `mode = "active"` / `"assisted"` / `"auto"` in config.toml to enable active automation. This ensures no unintended tool execution without explicit opt-in.
- **CVE tool preference**: `cve_search`, `cve_lookup`, and `patch_status_check` now prefer WebFetch-compatible tools before browser automation fallbacks.

### Removed

- `skill_card.yaml`, `skill_card.yml`, and `skill_card.json` files under `agents/skills/`.
- `references/` directories under `agents/skills/`.

## [0.6.0] - 2026-06-22

### Added
- Loop Runtime automation skeleton with `Observe -> Decide -> Act -> Verify -> Record -> Next` flow.
- `LoopDecision` metadata fields: `trigger`, `feedback_gate`, `exit_condition`, `required_artifact`, `required_capability`, and `selected_tool`.
- Automation runtime modules: decision tree, loop state, gate engine, rhythm classifier, quick cards, executor adapter layer, loop recorder, and report builder.
- Registered executor adapters for bounded tool execution. Red-team `active` / `auto` / `assisted` automation starts an active executor; explicitly registered adapters can execute scoped steps and return standard `ExecutionResult` objects.
- Scope-gated runtime execution: tool steps are checked through Tool Registry and Scope Gate before adapter execution.
- Artifact-driven progression: successful adapter output is saved through `ArtifactStore` and fed back into artifact gates before advancing.
- Retry handling for retryable adapter failures.
- Strict `ReportGate` mode covering seven report-readiness gates: core evidence, reproduction, impact proof, multi-ID/parameter check, scope proof, false-positive exclusion, parameter portability, and CIA impact.
- Controller brief output for `[loop-trigger:]`, `[feedback-gate:]`, and `[exit-condition:]`.
- Loop runtime tests covering adapter execution, scope blocking, retry, artifact saving, decision logging, and strict report gates.

### Changed
- Updated README, README_ZH, and instruction profile to describe the current Loop Runtime and adapter-based automation behavior.
- Updated install validation to require the new automation runtime files.
- Updated installer version to `0.6.0`.
- Aligned `config.toml` tool priority with README and template by adding `Current AI Agent`.

### Fixed
- Restored normal UTF-8 Chinese red-team activation and disable trigger text in `instruction.ctf.md`.
- Fixed Windows `hooks.json` template path escaping during install.
- Fixed direct import crash in `hooks/core/method_engine.py` by using the shared router mappings module.
- Fixed controller phase fallback so summarize/revise/new-objective prompts no longer inherit stale domain phases; only genuine continue prompts preserve the previous phase.
- Fixed prompt extraction fallback so explicit non-user `system`/`assistant` messages are not treated as user prompts, while role-less legacy messages remain supported.
- Fixed Scope Gate behavior for scoped tools with a target but no declared `in_scope`; these now return `missing_scope` instead of default allow.
- Fixed Loop Runtime verification so empty execution results cannot satisfy verification via Python's `all([])` behavior.
- Added regression coverage for method import, prompt role filtering, phase fallback, missing scope, and empty execution-result verification.

### Notes
- This release adds a real automation loop runtime and adapter execution path, but it does not hardcode direct shell, scanner, exploit, or network execution. Real tools must be wired through explicit scoped adapters.

## [0.5.0] - 2026-06-14

### Added
- Dedicated routing layer (`codex/router/`) with regex-based router engine supporting Chinese + English pattern detection, pack selector, leaf selector, and method engine.
- External skill adapters for ACS, hackskills, and qiushi reference repositories (`codex/router/adapters/`).
- Fine-grained sub-routers per domain: 5 web sub-routers, 4 AD sub-routers, 6 crypto sub-routers, 5 network protocol sub-routers, and 3 mobile sub-routers.
- Session patcher system (`codex/session_patcher/`) with two-tier refusal detector, JSONL session file cleaner with auto-backup, refusal-content replacement, and optional AI-powered rewrite.
- Cross-platform installer launchers: `install.ps1` for Windows PowerShell and `install.sh` for macOS/Linux bash.
- Templates directory with `hooks.json.template` and `config.toml.example`.
- Expanded test suite covering router, orchestrator, automation tools, controller, install, modes, and session patcher.
- Enhanced `scripts/validate.py` with per-subsystem file verification.

### Changed
- Updated `config.toml` to include `Current AI Agent` as the fifth preferred tool class.
- Refined installer with managed manifest tracking, idempotent upgrades, stale legacy path cleanup, and `--uninstall` support.
- Tightened phase-to-method escalation mappings with per-domain defaults.
- Router now uses dedicated `mappings.py` for all phase-to-router, router-to-pack, and phase-to-method lookups.

## [0.4.0] - 2026-05-18

### Changed
- Normalized the GitHub version around the effective `phase -> router -> pack -> leaf` runtime model.
- Reduced method emphasis to a soft hint instead of the primary routing axis.
- Tightened evidence inference to avoid overconfident `confirmed` labels.
- Aligned session-start, runtime, docs, and tests with actual pack-first behavior.

### Added
- Expanded domain routing for cloud, container, network, crypto, and mobile scenarios.
- Added dedicated detail packs for recon, API, auth, injection, file, business logic, cloud, container, network, crypto, and mobile.
- Expanded validation coverage for the new routing domains.
- Installer cleanup for known stale legacy runtime paths.

## [0.3.0] - 2026-05-14

### Changed
- Removed methodology layer; subdivided skills for smarter AI behavior during work phases.
- Added semantic judgment as fallback for phase detection.
- Optimized workflow routing based on community feedback.

### Added
- Overlay installation enablement. Thanks Nirvana.

## [0.2.0] - 2026-05-11

### Added
- Extended router/pack families beyond core phases.
- Initial validation and orchestration gate checks.
- Prompt-chain verification tests.

### Changed
- Improved prompt-chain text robustness. Thanks PINGS.
- Refined hook injection to stay lightweight.

## [0.1.0] - 2026-05-07

### Added
- Initial release offering `normal`, `redteam-light`, and `redteam-full` modes.
- Structured JSON runtime state with session isolation.
- Rule-first phase detection with semantic fallback.
- Pack-first routing mainline: `phase -> router -> pack -> leaf`.
- Core phase coverage spanning web, AD, post-exploitation, reverse engineering, code-audit, payload, and evasion.
- Managed incremental installer for Python and PowerShell.
- Reference method layer and technology routing layer from three external skill repositories.

[1.3.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v1.3.0
[1.2.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v1.2.0
[1.1.7]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v1.1.7
[1.0.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v1.0.0
[0.6.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.6.0
[0.5.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.5.0
[0.4.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.4.0
[0.3.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.3.0
[0.2.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.2.0
[0.1.0]: https://github.com/chAng-L19/codex-redteam-mode/releases/tag/v0.1.0

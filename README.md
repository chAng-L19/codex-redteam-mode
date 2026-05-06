# Codex Red Team Opt-In Mode

> **Professional offensive routing — only when you explicitly turn it on.**

A lightweight Codex profile that keeps your assistant in **normal mode by default**, and only switches into **red-team doctrine** when you deliberately enable it.

---

## Why this exists

Most red-team profiles fail in one of two ways:

- they are **always on**, so ordinary work gets dragged into offensive framing
- they inject too much static context, causing **context pollution**, drift, or recovery issues

This repository fixes that by using a **mode-gated design**:

- **Default mode:** normal
- **Red-team mode:** explicit opt-in only
- **Context footprint:** intentionally small
- **Behavior:** phase-aware, evidence-first, low-noise

---

## Features

- **Opt-in only** red-team mode
- **Session-safe** default reset to normal mode
- **Lightweight hooks** that avoid context bloat
- **Phase-aware routing** for:
  - web exploitation
  - AD / credential work
  - post-exploitation
  - reverse / malware / loaders
  - payload shaping
- **Clean disable path** back to normal mode
- **Burp-first** preference for Burp-native evidence
- **Playbook references** for each attack phase

---

## Mode switching

### Enable red-team mode
Use any of these:

```text
进入红队模式
开启红队模式
/redteam on
enable red team mode
```

### Disable red-team mode
Use any of these:

```text
退出红队模式
关闭红队模式
/redteam off
disable red team mode
```

---

## Repository layout

```text
.codex/
  AGENTS.md
  hooks/
    session-start-context.py
    hook-security-context-hook.py
.agents/
  skills/
    red-team-command-doctrine/
      SKILL.md
      references/
        PHASE-MATRIX.md
        MODE-STATE-MACHINE.md
        OPSEC-CHECKS.md
        phases/
templates/
  hooks.json.template
  config.toml.example
scripts/
  install.ps1
  uninstall.ps1
  validate.ps1
docs/
  BEHAVIOR.md
  PHASE-MATRIX.md
  MODE-STATE-MACHINE.md
  DESIGN.md
  EXAMPLES.md
  TROUBLESHOOTING.md
  ROLLBACK.md
CHANGELOG.md
```

---

## What gets installed

### `.codex/AGENTS.md`
Sets the high-level behavior contract:
- normal mode by default
- red-team mode is explicit opt-in
- tool preferences remain lightweight

### `session-start-context.py`
Resets the session state to **normal mode** on new session start.

### `hook-security-context-hook.py`
Handles:
- explicit mode on/off switching
- state persistence in temp
- phase detection after red-team mode is enabled

### `red-team-command-doctrine`
A compact governance skill used for:
- offensive phase discipline
- anti-drift
- low-noise routing
- explicit next-step posture

It ships with:
- per-phase playbooks
- a phase matrix
- a mode state machine
- OPSEC pre-broadening checks

---

## Installation

### Option A — Manual
Copy these files into your Codex home:

- `.codex/AGENTS.md`
- `.codex/hooks/session-start-context.py`
- `.codex/hooks/hook-security-context-hook.py`
- `.agents/skills/red-team-command-doctrine/SKILL.md`
- `.agents/skills/red-team-command-doctrine/references/*`

Then render `templates/hooks.json.template` into your real `hooks.json`, replacing:

- `{{CODEX_HOME_WIN}}` with your actual Codex home path

### Option B — PowerShell installer
Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The installer will:
- create missing directories
- back up existing files
- copy hooks and skill files
- render `hooks.json`

## Validation

After install:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate.ps1
```

## Rollback

To remove the installed files:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

---

## Included doctrine references

- `docs/PHASE-MATRIX.md`
- `docs/MODE-STATE-MACHINE.md`
- `docs/DESIGN.md`
- `docs/EXAMPLES.md`
- `docs/TROUBLESHOOTING.md`
- `docs/ROLLBACK.md`

---

## Safety design

This project intentionally avoids:

- default always-on red-team behavior
- large session-start prompt injection
- forcing offensive routing during normal work
- polluting context with huge governance blocks

The goal is simple:

> **Normal until explicitly armed.**

---

## Notes

- `config.toml.example` is a **reference**, not a full drop-in replacement
- your actual `config.toml` may include personal plugins, models, MCP servers, or local paths
- the hooks are UTF-8 aware and support Chinese enable/disable commands

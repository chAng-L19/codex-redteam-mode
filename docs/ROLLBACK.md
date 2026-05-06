# Rollback

## Manual rollback

Restore any `.bak` files created by the installer back to:

- `.codex/AGENTS.md`
- `.codex/hooks.json`
- `.codex/hooks/session-start-context.py`
- `.codex/hooks/hook-security-context-hook.py`
- `.agents/skills/red-team-command-doctrine/SKILL.md`

## Uninstall

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

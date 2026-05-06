param(
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [string]$AgentsHome = "$env:USERPROFILE\.agents"
)

$ErrorActionPreference = 'Stop'

$paths = @(
  "$CodexHome\hooks\session-start-context.py",
  "$CodexHome\hooks\hook-security-context-hook.py",
  "$CodexHome\hooks.json",
  "$AgentsHome\skills\red-team-command-doctrine"
)

foreach ($p in $paths) {
  if (Test-Path -LiteralPath $p) {
    Remove-Item -LiteralPath $p -Recurse -Force
  }
}

Write-Host 'Removed installed red-team mode files.' -ForegroundColor Yellow
Write-Host 'Restore your .bak copies if needed.' -ForegroundColor Yellow

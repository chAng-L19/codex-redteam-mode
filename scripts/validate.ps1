param(
  [string]$CodexHome = "$env:USERPROFILE\.codex"
)

$ErrorActionPreference = 'Stop'

Write-Host '[1/3] Checking files...' -ForegroundColor Cyan
$files = @(
  "$CodexHome\AGENTS.md",
  "$CodexHome\hooks.json",
  "$CodexHome\hooks\session-start-context.py",
  "$CodexHome\hooks\hook-security-context-hook.py"
)
$files | ForEach-Object {
  if (-not (Test-Path -LiteralPath $_)) { throw "Missing: $_" }
}

Write-Host '[2/3] Python syntax...' -ForegroundColor Cyan
python -m py_compile "$CodexHome\hooks\session-start-context.py" "$CodexHome\hooks\hook-security-context-hook.py"
if ($LASTEXITCODE -ne 0) { throw 'Python syntax validation failed.' }

Write-Host '[3/3] Hooks enabled hint...' -ForegroundColor Cyan
Get-Content "$CodexHome\hooks.json" -Raw | Select-String -Pattern 'UserPromptSubmit|SessionStart' | Out-Null

Write-Host 'Validation passed.' -ForegroundColor Green

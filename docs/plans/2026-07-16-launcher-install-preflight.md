# Model-aware Launcher and Install Preflight Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the missing model-aware Codex launcher and make installation source validation happen before any destructive upgrade cleanup.

**Architecture:** A standalone standard-library launcher will resolve the requested model, select one installed prompt profile, create a unique process-local instructions file, invoke the real Codex binary with a final config override, and remove the file in `finally`. The installer will own a declarative source-requirement list and validate it immediately after argument/path resolution, before loading prior manifests into a cleanup transaction.

**Tech Stack:** Python 3.11 standard library (`argparse`-free argument scanning, `fnmatch`, `json`, `pathlib`, `shutil`, `subprocess`, `tempfile`, `tomllib`), pytest, existing `tomlkit` installer dependency.

---

### Task 1: Guard cleanup with deployment-source preflight

**Files:**
- Modify: `tests/test_install.py`
- Modify: `scripts/install.py:16-24, 475-484, 630-656`

**Step 1: Write the failing source-inventory test**

Add tests that express the new public behavior:

```python
def test_deployment_source_preflight_accepts_repository() -> None:
    install.preflight_deployment_sources(REPO_ROOT)


def test_deployment_source_preflight_reports_missing_launcher(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "codex").mkdir(parents=True)
    with pytest.raises(install.InstallPreflightError, match=r"codex[/\\\\]launcher\.py"):
        install.preflight_deployment_sources(repo)
```

**Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests/test_install.py::test_deployment_source_preflight_accepts_repository tests/test_install.py::test_deployment_source_preflight_reports_missing_launcher
```

Expected: FAIL because `preflight_deployment_sources` and `InstallPreflightError` do not exist.

**Step 3: Implement the source inventory and preflight**

In `scripts/install.py`, add:

```python
class InstallPreflightError(RuntimeError):
    pass


def deployment_source_requirements(repo_root: Path) -> tuple[list[Path], list[Path]]:
    files = [
        repo_root / "config.toml",
        repo_root / "instruction.ctf.md",
        repo_root / "templates" / "hooks.json.template",
        repo_root / "codex" / "launcher.py",
        repo_root / "codex" / "AGENTS.md",
        repo_root / "codex" / "hooks" / "session-start-context.py",
        repo_root / "codex" / "hooks" / "hook-security-context-hook.py",
        repo_root / "codex" / "hooks" / "redteam_state.py",
    ]
    directories = [
        repo_root / "codex" / "hooks" / "core",
        repo_root / "codex" / "router",
        repo_root / "codex" / "orchestrator",
        repo_root / "codex" / "automation",
        repo_root / "codex" / "session_patcher",
        repo_root / "codex" / "prompts",
    ]
    files.extend(skill_dir / "SKILL.md" for skill_dir in repo_skill_dirs(repo_root))
    files.extend((repo_root / "codex" / "prompts").glob("Jailbreak*.md"))
    return files, directories


def preflight_deployment_sources(repo_root: Path) -> None:
    files, directories = deployment_source_requirements(repo_root)
    invalid = [path for path in files if not path.is_file()]
    invalid.extend(path for path in directories if not path.is_dir())
    if invalid:
        details = "\n".join(f"  - {path}" for path in invalid)
        raise InstallPreflightError(f"install source preflight failed:\n{details}")
```

Call `preflight_deployment_sources(repo_root)` in `main()` after the uninstall early return and before config preflight, manifest loading, transaction creation, or cleanup planning. Catch `InstallPreflightError` beside `ManifestValidationError` and exit with status 2.

**Step 4: Add and run the destructive-order integration test**

Create a minimal copied installer tree with no launcher, a project marker, and a manifest that records the marker. Execute that installer with `--project-home`; assert exit 2, stderr contains `install source preflight failed`, and the marker and manifest still exist.

Run the three focused tests and expect PASS.

**Step 5: Commit**

```powershell
git add scripts/install.py tests/test_install.py
git commit -m "fix: preflight install sources before cleanup"
```

### Task 2: Add model and profile selection primitives

**Files:**
- Create: `codex/launcher.py`
- Create: `tests/test_launcher.py`

**Step 1: Write failing model-selection tests**

Load `codex/launcher.py` with `importlib.util` and cover:

```python
@pytest.mark.parametrize("args, expected", [
    (["--model", "gpt-5.6-codex"], "gpt-5.6-codex"),
    (["--model=gpt-5.5-codex"], "gpt-5.5-codex"),
    (["-m", "gpt-5.4-codex"], "gpt-5.4-codex"),
    (["-c", 'model="gpt-5.6-sol"'], "gpt-5.6-sol"),
])
def test_extract_cli_model(args: list[str], expected: str) -> None:
    assert launcher.extract_cli_model(args) == expected
```

Also test precedence `CLI > CODEX_MODEL > config model > unknown` and longest-pattern profile selection with default fallback.

**Step 2: Run and verify RED**

Run `python -m pytest -q tests/test_launcher.py -k "model or profile"`.

Expected: FAIL because `codex/launcher.py` is missing.

**Step 3: Implement minimal pure functions**

Add constants matching `scripts/install.py` and implement:

```python
def extract_cli_model(args: Sequence[str]) -> str: ...
def read_config(codex_home: Path) -> dict[str, object]: ...
def resolve_model(args: Sequence[str], env: Mapping[str, str], config: Mapping[str, object]) -> tuple[str, str]: ...
def profile_mapping(config: Mapping[str, object]) -> dict[str, str]: ...
def select_profile(model: str, mapping: Mapping[str, str], prompts_dir: Path) -> tuple[str, str, Path]: ...
```

Use `tomllib`; sanitize every configured filename with `Path(filename).name`; require `prompt_path.is_file()`; fall back to the configured default and then the built-in default.

**Step 4: Run and verify GREEN**

Run the model/profile tests and expect PASS.

**Step 5: Commit**

```powershell
git add codex/launcher.py tests/test_launcher.py
git commit -m "feat: add launcher model profile selection"
```

### Task 3: Generate one process-local system instruction file

**Files:**
- Modify: `codex/launcher.py`
- Modify: `tests/test_launcher.py`

**Step 1: Write failing instruction-generation tests**

Build a temporary Codex Home containing:

- `redteam-mode/system-instructions.md` with a preserved/base prefix and a model catalog marker;
- two prompt profiles with distinct sentinel text;
- config profile mappings.

Assert `build_session_instructions(...)` includes the prefix and selected sentinel, excludes the unselected sentinel and automatic catalog, and creates the file inside `redteam-mode` with `.SESSION.md` suffix.

**Step 2: Run and verify RED**

Expected: FAIL because the generation function is missing.

**Step 3: Implement generation**

Implement:

```python
def base_system_instructions(shared_path: Path) -> str:
    content = shared_path.read_text(encoding="utf-8-sig")
    marker = "# Automatic model system profile router"
    return content.split(marker, 1)[0].rstrip()


def build_session_instructions(codex_home: Path, profile: str, filename: str, prompt_path: Path) -> Path:
    # tempfile.NamedTemporaryFile(delete=False, dir=redteam_dir, ...)
    # write base prefix + one selected profile and return the closed path
```

Reject a missing or empty shared system file with `LauncherError`. Use a unique temporary file and UTF-8.

**Step 4: Run and verify GREEN**

Run the focused instruction tests and expect PASS.

**Step 5: Commit**

```powershell
git add codex/launcher.py tests/test_launcher.py
git commit -m "feat: build per-session launcher instructions"
```

### Task 4: Launch Codex safely and always clean up

**Files:**
- Modify: `codex/launcher.py`
- Modify: `tests/test_launcher.py`

**Step 1: Write failing process integration tests**

Use `CODEX_REDTEAM_CODEX_BIN` to point to a temporary fake executable. The fake process writes its argv and the referenced instruction content to a capture file, then exits with a chosen code.

Assert:

- all original argv items are preserved in order;
- the final two argv items are `-c` and a TOML-compatible absolute `model_instructions_file="...SESSION.md"` override;
- the fake process can read the file while running;
- launcher returns the child exit code;
- the session file no longer exists afterward;
- missing executable returns 127 and leaves no session file;
- recursion candidates matching launcher/wrappers are rejected.

**Step 2: Run and verify RED**

Expected: FAIL because process execution and cleanup are missing.

**Step 3: Implement process execution**

Implement:

```python
def resolve_codex_executable(env: Mapping[str, str], launcher_path: Path) -> str: ...
def instruction_override(path: Path) -> str:
    return f"model_instructions_file={json.dumps(str(path))}"
def run(argv: Sequence[str], env: Mapping[str, str] | None = None) -> int: ...
def main() -> int: ...
```

Create instructions only after executable resolution succeeds. Invoke with `subprocess.run(..., check=False)` and return `returncode`. Remove the session path in `finally`, ignoring only `FileNotFoundError`. Print concise launcher errors to stderr and return 127.

**Step 4: Run and verify GREEN**

Run `python -m pytest -q tests/test_launcher.py` and expect all tests PASS.

**Step 5: Commit**

```powershell
git add codex/launcher.py tests/test_launcher.py
git commit -m "feat: launch codex with isolated model instructions"
```

### Task 5: Validate a real temporary installation

**Files:**
- Modify: `tests/test_install.py` only if launcher-specific stale assertions remain
- Modify: `scripts/validate.py` only if source-tree path handling needs correction

**Step 1: Run launcher/install integration tests**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests/test_launcher.py tests/test_install.py::test_project_home_install_writes_under_dot_dirs tests/test_install.py::test_installed_hook_commands_support_windows_shell_metacharacters
```

Expected after Tasks 1-4: launcher tests PASS; installation proceeds past the former `FileNotFoundError`. Any failure must be classified as launcher-specific or pre-existing test drift before editing assertions.

**Step 2: Correct only launcher-layout assertions**

The project install must assert these files exist:

```python
assert (project / ".codex" / "redteam-mode" / "launcher.py").is_file()
assert (project / ".codex" / "redteam-mode" / "codex-redteam.cmd").is_file()
assert (project / ".codex" / "redteam-mode" / "codex-redteam").is_file()
assert (project / ".codex" / "redteam-mode" / "system-instructions.md").is_file()
```

Do not repair unrelated prompt-text/config-path test drift in this task.

**Step 3: Run a manual install/validate/uninstall closure**

Use a fresh temporary project directory:

```powershell
python scripts/install.py --project-home $tempProject
python scripts/validate.py --codex-home ($tempProject + '\.codex')
python scripts/install.py --project-home $tempProject --uninstall
```

Expected: all three commands exit 0; installed launcher files exist before uninstall and are removed afterward.

**Step 4: Run the full suite**

Run `python -m pytest -q --tb=short`.

Expected: no launcher/preflight failures. Report unrelated pre-existing failures explicitly instead of broadening this fix.

**Step 5: Commit**

```powershell
git add tests/test_install.py scripts/validate.py
git commit -m "test: cover launcher installation lifecycle"
```

### Task 6: Final review and handoff

**Files:**
- Review: `codex/launcher.py`
- Review: `scripts/install.py`
- Review: `tests/test_launcher.py`
- Review: `tests/test_install.py`

**Step 1: Run static verification**

Run AST parsing for all Python files and `git diff --check`.

**Step 2: Re-run focused and full verification**

Freshly run the launcher suite, install lifecycle, source validator, and full pytest suite. Record exact pass/fail counts.

**Step 3: Review the diff**

Confirm no unrelated findings from `security_audit_report.md` were implemented and that the report remains untracked unless the user separately requests it.

**Step 4: Commit any final test-only correction**

Only if needed; otherwise leave the focused commits intact.

**Step 5: Handoff**

Report changed files, launcher behavior, preflight ordering guarantee, test evidence, and any unrelated pre-existing failures.

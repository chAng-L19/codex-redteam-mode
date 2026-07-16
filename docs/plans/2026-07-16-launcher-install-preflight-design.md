# Model-aware Launcher and Install Preflight Design

## Goal

Restore the documented `codex-redteam` CLI launcher and ensure an install or upgrade cannot delete an existing managed installation when a required source artifact is missing.

## Scope

This change is limited to the launcher-related high-severity finding:

- add the missing `codex/launcher.py`;
- validate required installation sources before beginning a transaction or applying upgrade cleanup;
- add focused launcher and installer regression tests;
- update stale launcher-specific validation expectations only where required by this fix.

It does not change normal/red-team prompt policy, manifest trust rules, session patching, or automation behavior.

## Launcher architecture

`codex/launcher.py` is copied to `<CODEX_HOME>/redteam-mode/launcher.py` and invoked by the generated Windows and POSIX wrappers. It determines its Codex Home from its installed location, then launches the real `codex` executable from `PATH`.

Model selection follows the documented precedence:

1. CLI `--model VALUE`, `--model=VALUE`, `-m VALUE`, `-m=VALUE`, `-c model=VALUE`, or `-c model="VALUE"`;
2. `CODEX_MODEL`;
3. `<CODEX_HOME>/config.toml` key `model`;
4. `unknown`, which selects the default profile.

All original user arguments are passed through unchanged. The launcher adds one final Codex configuration override for `model_instructions_file`; placing it last makes the process-local session file authoritative without modifying the user's persistent config.

## Session instruction generation

The installed shared `redteam-mode/system-instructions.md` remains the source for preserved user instructions and base instructions. The launcher reads its installer metadata and extracts the content before the automatic model catalog. It then appends only the selected prompt file from `<CODEX_HOME>/prompts/`.

Profile mapping comes from `[redteam.model_prompt_profiles]` in `<CODEX_HOME>/config.toml`, merged over the built-in GPT-5.4/5.5/5.6/default mapping. Configured filenames are reduced to their basename and must resolve to a regular file inside `<CODEX_HOME>/prompts`; a missing specialized profile falls back to `default`.

Each invocation creates a uniquely named file under `<CODEX_HOME>/redteam-mode/` using an exclusive temporary-file primitive. The file name includes the selected profile basename and a random session suffix. The launcher removes the file in `finally` after Codex exits, including launch failures and interrupts.

## Executable resolution and recursion safety

The real executable defaults to `codex`/`codex.exe` discovered through `PATH`. `CODEX_REDTEAM_CODEX_BIN` provides an explicit override for tests and unusual installations.

The resolved executable must not be the launcher itself or either generated wrapper. If no executable is found, the launcher exits with a concise error and still removes the session instruction file.

The child exit code is returned unchanged. Signals and keyboard interrupts are propagated using normal subprocess behavior.

## Install preflight

The installer defines the complete set of source files and directories needed for deployment. Before `begin_transaction`, upgrade cleanup, config writes, or hook writes, it verifies:

- every required source file exists and is a regular file;
- every copied source tree exists and is a directory;
- every skill directory contains `SKILL.md`.

Failure raises a dedicated preflight error listing all missing or invalid sources. Dry-run performs the same source validation because a preview that cannot actually install is misleading.

The existing transaction mechanism remains unchanged after preflight succeeds.

## Tests

Focused tests will cover:

- installer preflight rejects a missing launcher before cleanup and preserves an existing managed marker;
- the source tree contains every deployment input required by preflight;
- launcher model precedence and profile fallback;
- argument passthrough plus the final process-local `model_instructions_file` override;
- child exit-code propagation;
- session instruction file contains only the selected profile and is removed on success and launch failure;
- Windows/POSIX wrapper installation and validator expectations through the existing project-install integration tests.

The tests use a fake Codex executable/script and temporary Codex Home; they do not invoke a real Codex process or network service.

## Acceptance criteria

- A clean project-level install completes and validates.
- Missing deployment sources cause a non-zero preflight failure without deleting existing managed files.
- `codex-redteam --model ...` starts the configured fake Codex binary with all user arguments and a valid per-session instruction override.
- The per-session file is always removed after child termination.
- Focused tests pass, and the full suite has no launcher-related failures.

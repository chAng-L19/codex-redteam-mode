#!/usr/bin/env python3
from __future__ import annotations

"""Process-local model-aware launcher for an installed Codex profile."""

from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Mapping, Sequence


DEFAULT_PROFILE_FILES = {
    "gpt-5.6*": "Jailbreak.gpt-5.6.md",
    "gpt-5.5*": "Jailbreak.gpt-5.5.md",
    "gpt-5.4*": "Jailbreak.gpt-5.4.md",
    "default": "Jailbreak.default.md",
}


class LauncherError(RuntimeError):
    pass


def _safe_filename(value: str) -> str:
    return Path(value.replace("\\", "/")).name


def _model_from_config_override(value: str) -> str:
    key, separator, raw = value.partition("=")
    if not separator or key.strip() != "model" or not raw.strip():
        return ""
    try:
        parsed = tomllib.loads(f"model = {raw.strip()}").get("model")
    except tomllib.TOMLDecodeError:
        parsed = raw.strip().strip('"').strip("'")
    return parsed.strip() if isinstance(parsed, str) else ""


def extract_cli_model(args: Sequence[str]) -> str:
    explicit_model = ""
    configured_model = ""
    index = 0
    while index < len(args):
        argument = str(args[index])
        if argument == "--":
            break
        if argument in {"--model", "-m"} and index + 1 < len(args):
            explicit_model = str(args[index + 1]).strip()
            index += 2
            continue
        if argument.startswith("--model=") or argument.startswith("-m="):
            explicit_model = argument.split("=", 1)[1].strip()
        elif argument.startswith("--config="):
            configured = _model_from_config_override(argument.split("=", 1)[1])
            if configured:
                configured_model = configured
        elif argument in {"-c", "--config"} and index + 1 < len(args):
            configured = _model_from_config_override(str(args[index + 1]))
            if configured:
                configured_model = configured
            index += 2
            continue
        index += 1
    return explicit_model or configured_model


def resolve_model(
    args: Sequence[str],
    env: Mapping[str, str],
    config: Mapping[str, object],
) -> tuple[str, str]:
    cli_model = extract_cli_model(args)
    if cli_model:
        return cli_model, "argument"
    env_model = str(env.get("CODEX_MODEL", "")).strip()
    if env_model:
        return env_model, "environment"
    config_model = config.get("model")
    if isinstance(config_model, str) and config_model.strip():
        return config_model.strip(), "config"
    return "unknown", "default"


def profile_mapping(config: Mapping[str, object]) -> dict[str, str]:
    mapping = dict(DEFAULT_PROFILE_FILES)
    redteam = config.get("redteam")
    configured = redteam.get("model_prompt_profiles") if isinstance(redteam, Mapping) else None
    if not isinstance(configured, Mapping):
        return mapping
    for raw_pattern, raw_filename in configured.items():
        pattern = str(raw_pattern).strip()
        if not pattern or not isinstance(raw_filename, str) or not raw_filename.strip():
            continue
        mapping[pattern] = _safe_filename(raw_filename.strip())
    return mapping


def select_profile(model: str, mapping: Mapping[str, str], prompts_dir: Path) -> tuple[str, str, Path]:
    normalized = model.casefold()
    selected_pattern = "default"
    selected_filename = mapping.get("default", DEFAULT_PROFILE_FILES["default"])
    patterns = sorted((key for key in mapping if key.casefold() != "default"), key=len, reverse=True)
    for pattern in patterns:
        lowered = pattern.casefold()
        if fnmatchcase(normalized, lowered) or (
            not any(character in lowered for character in "*?[") and normalized.startswith(lowered)
        ):
            selected_pattern = pattern
            selected_filename = mapping[pattern]
            break

    safe_filename = _safe_filename(str(selected_filename))
    selected_path = prompts_dir / safe_filename
    if selected_path.is_file():
        return selected_pattern, safe_filename, selected_path

    default_filename = _safe_filename(str(mapping.get("default", DEFAULT_PROFILE_FILES["default"])))
    default_path = prompts_dir / default_filename
    if default_path.is_file():
        return "default", default_filename, default_path

    builtin_path = prompts_dir / DEFAULT_PROFILE_FILES["default"]
    if builtin_path.is_file():
        return "default", DEFAULT_PROFILE_FILES["default"], builtin_path
    raise LauncherError(f"model prompt profile not found: {selected_path}")


def build_session_instructions(
    codex_home: Path,
    profile: str,
    filename: str,
    prompt_path: Path,
) -> Path:
    redteam_dir = codex_home / "redteam-mode"
    shared_path = redteam_dir / "system-instructions.md"
    try:
        shared_content = shared_path.read_text(encoding="utf-8-sig")
        profile_content = prompt_path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise LauncherError(f"could not read launcher instructions: {exc}") from exc
    router_boundary = "# Automatic model system profile router"
    if router_boundary not in shared_content:
        raise LauncherError(f"system instructions router boundary missing: {shared_path}")
    base_content = shared_content.rsplit(router_boundary, 1)[0].rstrip()
    if not base_content or not profile_content:
        raise LauncherError("base or selected model instructions are empty")

    rendered = (
        f"{base_content}\n\n"
        f"# Active model system profile: {profile}\n\n"
        f"Profile file: `{filename}`\n\n"
        f"{profile_content}\n"
    )
    redteam_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"system-instructions.{_safe_filename(filename)}."
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=prefix,
            suffix=".SESSION.md",
            dir=redteam_dir,
            delete=False,
        ) as handle:
            handle.write(rendered)
            return Path(handle.name)
    except OSError as exc:
        raise LauncherError(f"could not write session instructions: {exc}") from exc


def read_config(codex_home: Path) -> dict[str, object]:
    config_path = codex_home / "config.toml"
    if not config_path.is_file():
        return {}
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LauncherError(f"could not read Codex config: {exc}") from exc
    return config if isinstance(config, dict) else {}


def _resolved_executable(value: str) -> Path | None:
    discovered = shutil.which(value)
    if discovered:
        return Path(discovered).resolve(strict=False)
    candidate = Path(value).expanduser()
    return candidate.resolve(strict=False) if candidate.is_file() else None


def resolve_codex_executable(env: Mapping[str, str], launcher_path: Path) -> str:
    configured = str(env.get("CODEX_REDTEAM_CODEX_BIN", "")).strip()
    executable = _resolved_executable(configured) if configured else _resolved_executable("codex")
    if executable is None:
        requested = configured or "codex"
        raise LauncherError(f"Codex executable not found: {requested}")

    launcher_dir = launcher_path.resolve(strict=False).parent
    forbidden = {
        str(path.resolve(strict=False)).casefold()
        for path in (
            launcher_path,
            launcher_dir / "codex-redteam.cmd",
            launcher_dir / "codex-redteam",
        )
    }
    if str(executable).casefold() in forbidden:
        raise LauncherError(f"Codex executable resolves to the launcher itself: {executable}")
    return str(executable)


def instruction_override(path: Path) -> str:
    return f"model_instructions_file={json.dumps(str(path.resolve(strict=False)))}"


def child_arguments(argv: Sequence[str], override: str) -> list[str]:
    arguments = [str(argument) for argument in argv]
    try:
        terminator_index = arguments.index("--")
    except ValueError:
        terminator_index = len(arguments)
    return [
        *arguments[:terminator_index],
        "-c",
        override,
        *arguments[terminator_index:],
    ]


def run(
    argv: Sequence[str],
    env: Mapping[str, str] | None = None,
    launcher_path: Path | None = None,
) -> int:
    runtime_env = dict(os.environ if env is None else env)
    installed_launcher = (launcher_path or Path(__file__)).resolve(strict=False)
    codex_home = installed_launcher.parent.parent
    config = read_config(codex_home)
    model, _ = resolve_model(argv, runtime_env, config)
    profile, filename, prompt_path = select_profile(
        model,
        profile_mapping(config),
        codex_home / "prompts",
    )
    executable = resolve_codex_executable(runtime_env, installed_launcher)
    session_path = build_session_instructions(codex_home, profile, filename, prompt_path)
    command = [executable, *child_arguments(argv, instruction_override(session_path))]
    try:
        try:
            completed = subprocess.run(command, env=runtime_env, check=False)
        except OSError as exc:
            raise LauncherError(f"could not start Codex: {exc}") from exc
        return int(completed.returncode)
    finally:
        try:
            session_path.unlink()
        except FileNotFoundError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(sys.argv[1:] if argv is None else argv)
    except LauncherError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())

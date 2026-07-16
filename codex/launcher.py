#!/usr/bin/env python3
from __future__ import annotations

import json
from fnmatch import fnmatchcase
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib


DEFAULT_PROFILE_FILES = {
    "gpt-5.6*": "Jailbreak.gpt-5.6.md",
    "gpt-5.5*": "Jailbreak.gpt-5.5.md",
    "gpt-5.4*": "Jailbreak.gpt-5.4.md",
    "default": "Jailbreak.default.md",
}
SYSTEM_PROFILE_END = "<!-- codex-redteam-system-profile:end -->"
ROUTER_HEADING = "# Automatic model system profile router"


def _assignment_value(raw: str, key: str) -> str:
    name, separator, value = raw.partition("=")
    if not separator or name.strip() != key:
        return ""
    try:
        parsed = tomllib.loads(f"{key} = {value}").get(key)
    except tomllib.TOMLDecodeError:
        parsed = value.strip().strip('"\'')
    return parsed.strip() if isinstance(parsed, str) else ""


def _record_config_assignment(raw: str, models: list[str]) -> None:
    name, separator, _ = raw.partition("=")
    if not separator:
        return
    normalized_name = name.strip()
    if normalized_name == "model_instructions_file":
        raise ValueError("model_instructions_file is managed by the launcher")
    if normalized_name != "model":
        return
    value = _assignment_value(raw, "model")
    if not value:
        raise ValueError("model argument must not be empty")
    models.append(value)


def _model_arguments(args: list[str]) -> list[str]:
    models: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument == "--":
            break
        if argument in {"--model", "-m"}:
            if index + 1 >= len(args) or not args[index + 1].strip() or args[index + 1].startswith("-"):
                raise ValueError(f"{argument} requires a model value")
            models.append(args[index + 1].strip())
            index += 2
            continue
        if argument.startswith("--model="):
            value = argument.split("=", 1)[1].strip()
            if not value:
                raise ValueError("--model requires a model value")
            models.append(value)
            index += 1
            continue
        if argument in {"-c", "--config"}:
            if index + 1 >= len(args):
                raise ValueError(f"{argument} requires a key=value argument")
            _record_config_assignment(args[index + 1], models)
            index += 2
            continue
        if argument.startswith("--config="):
            _record_config_assignment(argument.split("=", 1)[1], models)
        index += 1
    return models


def _read_config(config_path: Path) -> dict:
    try:
        value = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def resolve_model(args: list[str]) -> str:
    models = _model_arguments(args)
    if not models:
        raise ValueError("launcher requires an explicit model argument")
    distinct = {model.casefold() for model in models}
    if len(distinct) != 1:
        raise ValueError(f"conflicting model arguments: {', '.join(models)}")
    return models[0]


def profile_mapping(config_path: Path) -> dict[str, str]:
    mapping = dict(DEFAULT_PROFILE_FILES)
    redteam = _read_config(config_path).get("redteam")
    configured = redteam.get("model_prompt_profiles") if isinstance(redteam, dict) else None
    if isinstance(configured, dict):
        mapping.update(
            (str(pattern).strip(), filename.strip())
            for pattern, filename in configured.items()
            if str(pattern).strip() and isinstance(filename, str) and filename.strip()
        )
    return mapping


def select_profile(model: str, mapping: dict[str, str]) -> tuple[str, str]:
    normalized = model.casefold()
    patterns = sorted((key for key in mapping if key.casefold() != "default"), key=len, reverse=True)
    for pattern in patterns:
        lowered = pattern.casefold()
        if fnmatchcase(normalized, lowered) or (
            not any(character in lowered for character in "*?[") and normalized.startswith(lowered)
        ):
            return pattern, mapping[pattern]
    return "default", mapping.get("default", DEFAULT_PROFILE_FILES["default"])


def build_session_instructions(shared: str, profile: str, pattern: str, filename: str) -> str:
    body = shared.split(SYSTEM_PROFILE_END, 1)[1].lstrip() if SYSTEM_PROFILE_END in shared else shared
    body = body.split(f"\n{ROUTER_HEADING}", 1)[0].rstrip()
    return (
        f"{body}\n\n# Selected model system profile: {pattern}\n\n"
        f"Profile file: `{filename}`\n\n{profile.strip()}\n"
    )


def build_codex_command(args: list[str], session_path: Path, executable: str) -> list[str]:
    override = f"model_instructions_file={json.dumps(str(session_path))}"
    return [executable, *args, "-c", override]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    codex_home = Path(__file__).resolve().parents[1]
    config_path = codex_home / "config.toml"
    try:
        model = resolve_model(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    mapping = profile_mapping(config_path)
    pattern, filename = select_profile(model, mapping)
    profile_path = codex_home / "prompts" / Path(filename).name
    if not profile_path.is_file():
        pattern = "default"
        filename = mapping.get("default", DEFAULT_PROFILE_FILES["default"])
        profile_path = codex_home / "prompts" / Path(filename).name
    shared_path = codex_home / "redteam-mode" / "system-instructions.md"
    if not shared_path.is_file() or not profile_path.is_file():
        print("ERROR: installed system instructions or model profile is missing", file=sys.stderr)
        return 2

    content = build_session_instructions(
        shared_path.read_text(encoding="utf-8-sig"),
        profile_path.read_text(encoding="utf-8-sig"),
        pattern,
        profile_path.name,
    )
    runtime_dir = codex_home / "redteam-mode" / "state" / "system_instructions"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f"system-instructions.{profile_path.name}.",
        suffix=".SESSION.md",
        dir=runtime_dir,
        text=True,
    )
    os.close(descriptor)
    session_path = Path(temporary)
    session_path.write_text(content, encoding="utf-8")

    executable = os.environ.get("CODEX_REDTEAM_CODEX_BIN", "").strip() or shutil.which("codex")
    if not executable:
        session_path.unlink(missing_ok=True)
        print("ERROR: codex executable was not found", file=sys.stderr)
        return 127
    environment = dict(os.environ)
    environment["CODEX_MODEL"] = model
    environment["CODEX_REDTEAM_PROFILE_MODE"] = "single"
    environment["CODEX_REDTEAM_PINNED_MODEL"] = model
    environment["CODEX_REDTEAM_PINNED_PROFILE"] = pattern
    environment["CODEX_REDTEAM_PINNED_PROFILE_FILE"] = profile_path.name
    print(
        "提示：本启动器已加载单一 system profile。\n"
        f"启动模型：{model}\n锁定模型族：{pattern}\nProfile 文件：{profile_path.name}\n"
        "同一模型族的变体可以继续使用；切换到其他模型族不会更新 system instructions，"
        "下一次用户提示将被阻止。\n\n"
        "Notice: This launcher loaded a single system profile.\n"
        f"Launch model: {model}\nLocked model family: {pattern}\nProfile file: {profile_path.name}\n"
        "Variants in the same model family remain compatible. Switching to another model family "
        "will not update the system instructions, and the next user prompt will be blocked.",
        file=sys.stderr,
    )
    try:
        return subprocess.run(build_codex_command(args, session_path, executable), env=environment).returncode
    finally:
        session_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())

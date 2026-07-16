from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = REPO_ROOT / "codex" / "launcher.py"


def _load_launcher(path: Path = LAUNCHER_PATH):
    spec = importlib.util.spec_from_file_location("codex_redteam_launcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_launcher_home(tmp_path: Path) -> tuple[Path, Path]:
    codex_home = tmp_path / ".codex"
    redteam_dir = codex_home / "redteam-mode"
    prompts_dir = codex_home / "prompts"
    redteam_dir.mkdir(parents=True)
    prompts_dir.mkdir()
    installed_launcher = redteam_dir / "launcher.py"
    shutil.copy2(LAUNCHER_PATH, installed_launcher)
    (redteam_dir / "system-instructions.md").write_text(
        "# Preserved and base instructions\n\nBASE_SENTINEL\n\n"
        "# Automatic model system profile router\n\nUNSELECTED_CATALOG_SENTINEL\n",
        encoding="utf-8",
    )
    (prompts_dir / "Jailbreak.gpt-5.6.md").write_text("SELECTED_56_SENTINEL\n", encoding="utf-8")
    (prompts_dir / "Jailbreak.default.md").write_text("DEFAULT_SENTINEL\n", encoding="utf-8")
    (codex_home / "config.toml").write_text(
        'model = "config-model"\n\n'
        "[redteam.model_prompt_profiles]\n"
        '"gpt-5.6*" = "Jailbreak.gpt-5.6.md"\n'
        'default = "Jailbreak.default.md"\n',
        encoding="utf-8",
    )
    return codex_home, installed_launcher


def test_launcher_module_is_packaged() -> None:
    assert LAUNCHER_PATH.is_file()


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--model", "gpt-5.6-codex"], "gpt-5.6-codex"),
        (["--model=gpt-5.5-codex"], "gpt-5.5-codex"),
        (["-m", "gpt-5.4-codex"], "gpt-5.4-codex"),
        (["-m=gpt-5.6-sol"], "gpt-5.6-sol"),
        (["-c", 'model="gpt-5.5-sol"'], "gpt-5.5-sol"),
        (["--config", "model=gpt-5.4-sol"], "gpt-5.4-sol"),
        (["--config=model=gpt-5.6-sol"], "gpt-5.6-sol"),
    ],
)
def test_extract_cli_model(args: list[str], expected: str) -> None:
    launcher = _load_launcher()

    assert launcher.extract_cli_model(args) == expected


def test_resolve_model_uses_documented_precedence() -> None:
    launcher = _load_launcher()
    config = {"model": "config-model"}

    assert launcher.resolve_model(["--model", "cli-model"], {"CODEX_MODEL": "env-model"}, config) == (
        "cli-model",
        "argument",
    )
    assert launcher.resolve_model([], {"CODEX_MODEL": "env-model"}, config) == ("env-model", "environment")
    assert launcher.resolve_model([], {}, config) == ("config-model", "config")
    assert launcher.resolve_model([], {}, {}) == ("unknown", "default")


def test_extract_cli_model_stops_at_double_dash() -> None:
    launcher = _load_launcher()

    assert launcher.extract_cli_model(["--model", "real-model", "--", "--model", "prompt-text"]) == "real-model"
    assert launcher.extract_cli_model(["--", "--model", "prompt-text"]) == ""


def test_explicit_model_option_overrides_config_model_regardless_of_order() -> None:
    launcher = _load_launcher()

    assert launcher.extract_cli_model(["--model", "explicit", "-c", "model=configured"]) == "explicit"
    assert launcher.extract_cli_model(["-c", "model=configured", "-m", "explicit"]) == "explicit"


def test_child_arguments_insert_instruction_override_before_double_dash() -> None:
    launcher = _load_launcher()
    override = 'model_instructions_file="session.md"'

    assert launcher.child_arguments(["exec", "--", "prompt", "--model", "text"], override) == [
        "exec",
        "-c",
        override,
        "--",
        "prompt",
        "--model",
        "text",
    ]


def test_select_profile_prefers_longest_pattern_and_falls_back_to_default(tmp_path: Path) -> None:
    launcher = _load_launcher()
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    specialized = prompts / "specialized.md"
    broader = prompts / "broader.md"
    default = prompts / "default.md"
    for path in (specialized, broader, default):
        path.write_text(path.stem, encoding="utf-8")
    mapping = {
        "gpt-5*": broader.name,
        "gpt-5.6*": specialized.name,
        "default": default.name,
    }

    assert launcher.select_profile("gpt-5.6-codex", mapping, prompts) == (
        "gpt-5.6*",
        specialized.name,
        specialized,
    )

    specialized.unlink()
    assert launcher.select_profile("gpt-5.6-codex", mapping, prompts) == (
        "default",
        default.name,
        default,
    )


def test_profile_mapping_sanitizes_configured_filenames() -> None:
    launcher = _load_launcher()
    config = {"redteam": {"model_prompt_profiles": {"custom*": "../custom.md"}}}

    mapping = launcher.profile_mapping(config)

    assert mapping["custom*"] == "custom.md"
    assert mapping["default"] == "Jailbreak.default.md"


def test_build_session_instructions_contains_only_selected_profile(tmp_path: Path) -> None:
    launcher = _load_launcher()
    codex_home = tmp_path / ".codex"
    redteam_dir = codex_home / "redteam-mode"
    prompts_dir = codex_home / "prompts"
    redteam_dir.mkdir(parents=True)
    prompts_dir.mkdir()
    shared = redteam_dir / "system-instructions.md"
    shared.write_text(
        "<!-- metadata -->\n\n"
        "# Preserved and base instructions\n\nBASE_SENTINEL\n\n"
        "# Automatic model system profile router\n\n"
        "UNSELECTED_CATALOG_SENTINEL\n",
        encoding="utf-8",
    )
    selected = prompts_dir / "Jailbreak.selected.md"
    selected.write_text("SELECTED_PROFILE_SENTINEL\n", encoding="utf-8")

    session_path = launcher.build_session_instructions(
        codex_home,
        "gpt-selected*",
        selected.name,
        selected,
    )
    try:
        content = session_path.read_text(encoding="utf-8")
        assert session_path.parent == redteam_dir
        assert session_path.name.startswith("system-instructions.Jailbreak.selected.md.")
        assert session_path.name.endswith(".SESSION.md")
        assert "BASE_SENTINEL" in content
        assert "SELECTED_PROFILE_SENTINEL" in content
        assert "UNSELECTED_CATALOG_SENTINEL" not in content
        assert "# Automatic model system profile router" not in content
    finally:
        session_path.unlink(missing_ok=True)


def test_build_session_instructions_rejects_missing_router_boundary(tmp_path: Path) -> None:
    launcher = _load_launcher()
    codex_home = tmp_path / ".codex"
    redteam_dir = codex_home / "redteam-mode"
    prompts_dir = codex_home / "prompts"
    redteam_dir.mkdir(parents=True)
    prompts_dir.mkdir()
    (redteam_dir / "system-instructions.md").write_text("BASE_ONLY\n", encoding="utf-8")
    selected = prompts_dir / "selected.md"
    selected.write_text("SELECTED\n", encoding="utf-8")

    with pytest.raises(launcher.LauncherError, match="router boundary"):
        launcher.build_session_instructions(codex_home, "default", selected.name, selected)


def test_build_session_instructions_uses_last_router_boundary(tmp_path: Path) -> None:
    launcher = _load_launcher()
    codex_home = tmp_path / ".codex"
    redteam_dir = codex_home / "redteam-mode"
    prompts_dir = codex_home / "prompts"
    redteam_dir.mkdir(parents=True)
    prompts_dir.mkdir()
    boundary = "# Automatic model system profile router"
    (redteam_dir / "system-instructions.md").write_text(
        f"USER_TEXT_WITH_HEADING\n{boundary}\nBASE_AFTER_USER_HEADING\n{boundary}\nREAL_CATALOG\n",
        encoding="utf-8",
    )
    selected = prompts_dir / "selected.md"
    selected.write_text("SELECTED\n", encoding="utf-8")

    session_path = launcher.build_session_instructions(codex_home, "default", selected.name, selected)
    try:
        content = session_path.read_text(encoding="utf-8")
        assert "BASE_AFTER_USER_HEADING" in content
        assert "REAL_CATALOG" not in content
    finally:
        session_path.unlink(missing_ok=True)


def test_launcher_passes_arguments_uses_one_profile_and_cleans_session_file(tmp_path: Path) -> None:
    codex_home, installed_launcher = _write_launcher_home(tmp_path)
    capture_path = tmp_path / "capture.json"
    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        "import json, os, pathlib, sys, tomllib\n"
        "override = sys.argv[-1]\n"
        "config = tomllib.loads(override)\n"
        "instructions = pathlib.Path(config['model_instructions_file'])\n"
        "pathlib.Path(os.environ['CAPTURE_PATH']).write_text(json.dumps({\n"
        "    'args': sys.argv[1:],\n"
        "    'instruction_path': str(instructions),\n"
        "    'instruction_exists': instructions.is_file(),\n"
        "    'instruction_content': instructions.read_text(encoding='utf-8'),\n"
        "}), encoding='utf-8')\n"
        "raise SystemExit(int(os.environ['FAKE_EXIT_CODE']))\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "CODEX_REDTEAM_CODEX_BIN": sys.executable,
        "CAPTURE_PATH": str(capture_path),
        "FAKE_EXIT_CODE": "7",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    original_args = [str(fake_codex), "--model", "gpt-5.6-codex", "user argument"]

    result = subprocess.run(
        [sys.executable, "-B", str(installed_launcher), *original_args],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 7, result.stderr
    captured = json.loads(capture_path.read_text(encoding="utf-8"))
    assert captured["args"][:-2] == original_args[1:]
    assert captured["args"][-2] == "-c"
    override = tomllib.loads(captured["args"][-1])
    assert Path(override["model_instructions_file"]) == Path(captured["instruction_path"])
    assert captured["instruction_exists"] is True
    assert "BASE_SENTINEL" in captured["instruction_content"]
    assert "SELECTED_56_SENTINEL" in captured["instruction_content"]
    assert "DEFAULT_SENTINEL" not in captured["instruction_content"]
    assert "UNSELECTED_CATALOG_SENTINEL" not in captured["instruction_content"]
    assert not Path(captured["instruction_path"]).exists()
    assert list((codex_home / "redteam-mode").glob("*.SESSION.md")) == []


def test_launcher_missing_or_recursive_executable_fails_without_session_file(tmp_path: Path) -> None:
    codex_home, installed_launcher = _write_launcher_home(tmp_path)
    launcher = _load_launcher(installed_launcher)

    with pytest.raises(launcher.LauncherError, match="not found"):
        launcher.resolve_codex_executable(
            {"CODEX_REDTEAM_CODEX_BIN": str(tmp_path / "missing-codex")},
            installed_launcher,
        )
    with pytest.raises(launcher.LauncherError, match="launcher itself"):
        launcher.resolve_codex_executable(
            {"CODEX_REDTEAM_CODEX_BIN": str(installed_launcher)},
            installed_launcher,
        )

    assert list((codex_home / "redteam-mode").glob("*.SESSION.md")) == []


def test_launcher_cleans_session_file_when_child_start_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home, installed_launcher = _write_launcher_home(tmp_path)
    launcher = _load_launcher(installed_launcher)

    def fail_to_start(*args, **kwargs):
        raise OSError("simulated launch failure")

    monkeypatch.setattr(launcher.subprocess, "run", fail_to_start)
    env = {**os.environ, "CODEX_REDTEAM_CODEX_BIN": sys.executable}

    with pytest.raises(launcher.LauncherError, match="could not start Codex"):
        launcher.run(["--model", "gpt-5.6-codex"], env=env, launcher_path=installed_launcher)

    assert list((codex_home / "redteam-mode").glob("*.SESSION.md")) == []

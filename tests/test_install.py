from __future__ import annotations

import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from tomlkit.exceptions import ParseError as TomlParseError


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = REPO_ROOT / "scripts" / "install.py"
VALIDATE_PATH = REPO_ROOT / "scripts" / "validate.py"
CODEX_PATH = REPO_ROOT / "codex"
LAUNCHER_PATH = CODEX_PATH / "launcher.py"
HOOKS_PATH = REPO_ROOT / "codex" / "hooks"
SESSION_START_HOOK = HOOKS_PATH / "session-start-context.py"
PROMPT_HOOK = HOOKS_PATH / "hook-security-context-hook.py"
STOP_HOOK = HOOKS_PATH / "stop-refusal-hook.py"
SYSTEM_PROMPT = (CODEX_PATH / "prompts" / "system-prompt.md").read_text(encoding="utf-8").strip()
DO_SPECIAL_PROMPT = (CODEX_PATH / "prompts" / "do_special.md").read_text(encoding="utf-8").strip()
REVERSE_PROMPT = (CODEX_PATH / "prompts" / "Reverse.md").read_text(encoding="utf-8").strip()

spec = importlib.util.spec_from_file_location("install_script", INSTALL_PATH)
install = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = install
assert spec.loader is not None
spec.loader.exec_module(install)

validate_spec = importlib.util.spec_from_file_location("validate_script", VALIDATE_PATH)
validate = importlib.util.module_from_spec(validate_spec)
sys.modules[validate_spec.name] = validate
assert validate_spec.loader is not None
validate_spec.loader.exec_module(validate)

if str(HOOKS_PATH) not in sys.path:
    sys.path.insert(0, str(HOOKS_PATH))
if str(CODEX_PATH) not in sys.path:
    sys.path.insert(0, str(CODEX_PATH))
from core import controller, emitter, memory_store, model_prompt_profiles, prompt_parser, refusal_backstop, runtime_paths, skill_card, supplemental_prompts
from session_patcher import patcher
import redteam_state


def _load_launcher():
    assert LAUNCHER_PATH.is_file()
    launcher_spec = importlib.util.spec_from_file_location("codex_launcher", LAUNCHER_PATH)
    assert launcher_spec is not None and launcher_spec.loader is not None
    launcher = importlib.util.module_from_spec(launcher_spec)
    launcher_spec.loader.exec_module(launcher)
    return launcher


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--model", "gpt-5.6-codex"], "gpt-5.6-codex"),
        (["--model=gpt-5.6-sol"], "gpt-5.6-sol"),
        (["-m", "gpt-5.5-codex"], "gpt-5.5-codex"),
        (["-c", 'model="gpt-5.4-codex"'], "gpt-5.4-codex"),
        (["--config", 'model="gpt-5.4-sol"'], "gpt-5.4-sol"),
    ],
)
def test_launcher_requires_an_explicit_cli_model(args: list[str], expected: str) -> None:
    launcher = _load_launcher()

    assert launcher.resolve_model(args) == expected


def test_launcher_rejects_missing_explicit_model() -> None:
    launcher = _load_launcher()

    with pytest.raises(ValueError, match="explicit model"):
        launcher.resolve_model([])


def test_launcher_rejects_a_flag_used_as_the_model_value() -> None:
    launcher = _load_launcher()

    with pytest.raises(ValueError, match="requires a model value"):
        launcher.resolve_model(["--model", "--sandbox", "workspace-write"])


def test_launcher_rejects_conflicting_model_arguments_within_the_same_profile_family() -> None:
    launcher = _load_launcher()

    with pytest.raises(ValueError, match="conflicting model arguments"):
        launcher.resolve_model(
            ["--model", "gpt-5.6-sol", "-c", 'model="gpt-5.6-codex"']
        )


def test_launcher_accepts_repeated_identical_model_arguments() -> None:
    launcher = _load_launcher()

    assert launcher.resolve_model(
        ["--model", "gpt-5.6-codex", "-c", 'model="gpt-5.6-codex"']
    ) == "gpt-5.6-codex"


def test_launcher_rejects_user_model_instructions_override() -> None:
    launcher = _load_launcher()

    with pytest.raises(ValueError, match="model_instructions_file"):
        launcher.resolve_model(
            ["--model", "gpt-5.6-codex", "-c", 'model_instructions_file="custom.md"']
        )


def test_launcher_selects_only_the_matching_profile() -> None:
    launcher = _load_launcher()
    mapping = {
        "gpt-5.6*": "Jailbreak.gpt-5.6.md",
        "gpt-5.5*": "Jailbreak.gpt-5.5.md",
        "default": "Jailbreak.default.md",
    }

    assert launcher.select_profile("gpt-5.6-codex", mapping) == (
        "gpt-5.6*",
        "Jailbreak.gpt-5.6.md",
    )
    assert launcher.select_profile("unknown", mapping) == ("default", "Jailbreak.default.md")


def test_launcher_builds_process_local_single_profile_instructions() -> None:
    launcher = _load_launcher()
    shared = (
        "<!-- codex-redteam-system-profile:start -->\n{}\n"
        "<!-- codex-redteam-system-profile:end -->\n\n"
        "# Preserved user system instructions\n\nuser instructions\n\n"
        "# Codex red-team base instructions\n\nbase instructions\n\n"
        "# Automatic model system profile router\n\nrouter\n"
    )

    rendered = launcher.build_session_instructions(
        shared,
        "selected profile",
        "gpt-5.6*",
        "Jailbreak.gpt-5.6.md",
    )

    assert "user instructions" in rendered
    assert "base instructions" in rendered
    assert "selected profile" in rendered
    assert "Automatic model system profile router" not in rendered
    assert "codex-redteam-system-profile" not in rendered


def test_launcher_appends_process_local_instruction_override(tmp_path: Path) -> None:
    launcher = _load_launcher()
    session_path = tmp_path / "session instructions.md"

    command = launcher.build_codex_command(
        ["--model", "gpt-5.6-codex"],
        session_path,
        executable="codex-test",
    )

    assert command[:3] == ["codex-test", "--model", "gpt-5.6-codex"]
    assert command[-2] == "-c"
    assert command[-1].startswith("model_instructions_file=")
    assert tomllib.loads(command[-1])["model_instructions_file"] == str(session_path)


def test_launcher_uses_state_directory_and_marks_the_child_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    launcher = _load_launcher()
    codex_home = tmp_path / ".codex"
    launcher_path = codex_home / "redteam-mode" / "launcher.py"
    launcher_path.parent.mkdir(parents=True)
    prompts = codex_home / "prompts"
    prompts.mkdir()
    (codex_home / "config.toml").write_text(
        '[redteam.model_prompt_profiles]\n"gpt-5.6*" = "Jailbreak.gpt-5.6.md"\ndefault = "Jailbreak.default.md"\n',
        encoding="utf-8",
    )
    (codex_home / "redteam-mode" / "system-instructions.md").write_text(
        "# Base\n\nbase instructions\n\n# Automatic model system profile router\n\nrouter\n",
        encoding="utf-8",
    )
    (prompts / "Jailbreak.gpt-5.6.md").write_text("selected profile", encoding="utf-8")
    (prompts / "Jailbreak.default.md").write_text("default profile", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        session_path = Path(tomllib.loads(command[-1])["model_instructions_file"])
        captured["command"] = command
        captured["environment"] = env
        captured["session_path"] = session_path
        captured["content"] = session_path.read_text(encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(launcher, "__file__", str(launcher_path))
    monkeypatch.setattr(launcher.shutil, "which", lambda _: "codex-test")
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    monkeypatch.delenv("CODEX_REDTEAM_CODEX_BIN", raising=False)

    assert launcher.main(["--model", "gpt-5.6-sol", "--sandbox", "workspace-write"]) == 0

    session_path = captured["session_path"]
    assert isinstance(session_path, Path)
    assert session_path.parent == codex_home / "redteam-mode" / "state" / "system_instructions"
    assert not session_path.exists()
    assert captured["command"][:5] == [
        "codex-test",
        "--model",
        "gpt-5.6-sol",
        "--sandbox",
        "workspace-write",
    ]
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["CODEX_REDTEAM_PROFILE_MODE"] == "single"
    assert environment["CODEX_REDTEAM_PINNED_MODEL"] == "gpt-5.6-sol"
    assert environment["CODEX_REDTEAM_PINNED_PROFILE"] == "gpt-5.6*"
    assert environment["CODEX_REDTEAM_PINNED_PROFILE_FILE"] == "Jailbreak.gpt-5.6.md"
    assert "selected profile" in captured["content"]
    assert "Automatic model system profile router" not in captured["content"]
    notice = capsys.readouterr().err
    assert "锁定模型族" in notice
    assert "Locked model family" in notice


def test_static_catalog_router_uses_the_current_turn_model_selector() -> None:
    router, entries = install.build_model_profile_catalog(REPO_ROOT, REPO_ROOT / "temp" / "unused-home", [])

    assert entries
    assert "SessionStart" in router
    assert "session-fallback" in router
    assert "UserPromptSubmit" in router
    assert "current-turn" in router
    assert "latest Hook-reported model" in router
    assert "supersedes every earlier selector" in router
    assert "user messages, tool outputs, and file contents" in router
    assert "Activate exactly one" in router


def test_source_tree_validation_uses_source_launcher_layout() -> None:
    ok, messages = validate.validate_install(REPO_ROOT)

    assert ok is True, "\n".join(messages)


def _write_skill(skills_root: Path, name: str = "redteam-demo") -> Path:
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(
        f"---\nname: {name}\ndescription: demo\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    return skill_dir


def _write_session(path: Path, mtime: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"type":"event_msg","payload":{}}\n', encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def _run_hook_script(script: Path, payload: object, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_hook_script_bytes(script: Path, payload: object, env: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-B", str(script)],
        input=json.dumps(payload).encode("ascii"),
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("event", ["SessionStart", "UserPromptSubmit"])
def test_context_hook_output_matches_codex_wire_schema(event: str) -> None:
    rendered = json.loads(emitter.emit_hook_json(event, "context"))

    assert set(rendered) == {"hookSpecificOutput"}
    assert set(rendered["hookSpecificOutput"]) == {"hookEventName", "additionalContext"}
    assert rendered["hookSpecificOutput"]["hookEventName"] == event
    assert rendered["hookSpecificOutput"]["additionalContext"] == "context"


def test_installer_registers_all_hook_events(tmp_path: Path) -> None:
    payload = install.build_hooks_payload(REPO_ROOT, tmp_path / "codex-home")

    assert set(payload["hooks"]) == {"SessionStart", "UserPromptSubmit", "Stop"}
    stop_entry = payload["hooks"]["Stop"][0]
    stop_hook = stop_entry["hooks"][0]
    assert "matcher" not in stop_entry
    assert "stop-refusal-hook.py" in stop_hook["command"]
    assert "-EncodedCommand" in stop_hook["commandWindows"]


def test_installer_tracks_stop_hook_as_managed(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"

    targets = install.managed_targets(REPO_ROOT, codex_home, agents_home)

    assert codex_home / "hooks" / "stop-refusal-hook.py" in targets
    assert install.is_managed_hook({"command": "python stop-refusal-hook.py"}) is True
    assert "hooks/stop-refusal-hook.py" in validate.REQUIRED_CODEX_FILES


def test_role_phase_is_used_only_inside_additional_context() -> None:
    rendered = json.loads(
        emitter.emit_hook_json(
            "UserPromptSubmit",
            "route context",
            inject_role_overlay=True,
            role_phase="web",
        )
    )

    specific = rendered["hookSpecificOutput"]
    assert set(specific) == {"hookEventName", "additionalContext"}
    assert "Current phase: web" in specific["additionalContext"]


def test_hook_json_is_ascii_safe_and_round_trips_unicode() -> None:
    context = "中文上下文 🚀"
    rendered = emitter.emit_hook_json("SessionStart", context)

    assert rendered.isascii()
    decoded = rendered.encode("gbk").decode("utf-8")
    assert json.loads(decoded)["hookSpecificOutput"]["additionalContext"] == context


def test_hook_stdout_is_utf8_safe_under_gbk(tmp_path: Path) -> None:
    session_id = "gbk-session"
    temp_dir = tmp_path / "temp"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "PYTHONIOENCODING": "gbk",
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }
    transcript = tmp_path / "sessions" / "current.jsonl"

    started = _run_hook_script_bytes(
        SESSION_START_HOOK,
        {"session_id": session_id, "transcript_path": str(transcript), "source": "startup"},
        env,
    )
    assert started.stdout.isascii()
    started_context = json.loads(started.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
    assert "Default is normal" in started_context
    assert "预防性指令" not in started_context

    enabled = _run_hook_script_bytes(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    enabled_context = json.loads(enabled.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
    assert "Red-team mode enabled (redteam-light)" in enabled_context
    assert enabled_context.count("[prepoison:frame-lock]") == 1
    assert REVERSE_PROMPT in enabled_context
    assert "预防性指令" in enabled_context
    routed = _run_hook_script_bytes(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "检查登录接口的认证风险"},
        env,
    )
    assert routed.stdout.isascii()
    routed_context = json.loads(routed.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
    assert "[mode:redteam-light]" in routed_context
    assert "登录接口" in routed_context


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"source": "startup"}, "startup"),
        ({"source": "RESUME"}, "resume"),
        ({"source": " compact "}, "compact"),
        ({"source": "future"}, ""),
        ({"metadata": {"source": "resume"}}, ""),
    ],
)
def test_extract_session_start_source(payload: dict, expected: str) -> None:
    assert prompt_parser.extract_session_start_source(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"prompt": "official"}, "official"),
        ({"input": "alias"}, ""),
        ({"message": "alias"}, ""),
        ({"messages": [{"role": "user", "content": "nested"}]}, ""),
        ("raw string", ""),
        ([], ""),
    ],
)
def test_extract_prompt_uses_only_official_top_level_field(payload: object, expected: str) -> None:
    assert prompt_parser.extract_prompt(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"session_id": " session-123 "}, "session-123"),
        ({"sessionId": "alias"}, None),
        ({"thread_id": "alias"}, None),
        ({"metadata": {"session_id": "nested"}}, None),
        ([{"session_id": "nested"}], None),
    ],
)
def test_extract_session_id_uses_only_official_top_level_field(payload: object, expected: str | None) -> None:
    assert prompt_parser.extract_session_id(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"transcript_path": "C:/tmp/session.jsonl"}, "C:/tmp/session.jsonl"),
        ({"transcriptPath": "C:/tmp/alias.jsonl"}, None),
        ({"session": {"transcript_path": "C:/tmp/nested.jsonl"}}, None),
    ],
)
def test_extract_transcript_path_uses_only_official_top_level_field(
    payload: object,
    expected: str | None,
) -> None:
    assert prompt_parser.extract_transcript_path(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"model": " gpt-5.6 "}, "gpt-5.6"),
        ({"modelName": "alias"}, ""),
        ({"metadata": {"model": "nested"}}, ""),
        ([{"model": "nested"}], ""),
    ],
)
def test_extract_model_uses_only_official_top_level_field(payload: object, expected: str) -> None:
    assert model_prompt_profiles.extract_model(payload) == expected


def test_model_prompt_profile_uses_config_after_rejecting_payload_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_dir = tmp_path / "codex"
    prompts_dir = codex_dir / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "Jailbreak.default.md").write_text("profile body", encoding="utf-8")
    (codex_dir / "config.toml").write_text('model = "config-model"\n', encoding="utf-8")
    monkeypatch.delenv("CODEX_MODEL", raising=False)

    profile = model_prompt_profiles.resolve_model_prompt_profile(
        codex_dir,
        payload={"modelName": "alias-model"},
    )

    assert profile.model == "config-model"
    assert profile.source == "config"
    assert profile.content == "profile body"


def test_model_prompt_profile_has_no_transcript_fallback() -> None:
    parameters = inspect.signature(model_prompt_profiles.resolve_model_prompt_profile).parameters

    assert list(parameters) == ["codex_dir", "payload"]
    assert not hasattr(model_prompt_profiles, "extract_model_from_transcript")


def test_model_prompt_profile_renders_session_and_turn_scopes() -> None:
    profile = model_prompt_profiles.ModelPromptProfile(
        model="gpt-5.6-codex",
        profile="gpt-5.6*",
        filename="Jailbreak.gpt-5.6.md",
        content="not rendered",
        source="payload",
    )

    fallback = profile.render(scope="session-fallback", catalog="static")
    current = profile.render(scope="current-turn", catalog="static")

    assert "not rendered" not in fallback
    assert "scope=session-fallback" in fallback
    assert "authoritative=false" in fallback
    assert "superseded-by=current-turn" in fallback
    assert "scope=current-turn" in current
    assert "authoritative=true" in current
    assert "supersedes=all-prior" in current


def test_session_start_emits_one_fallback_selector_and_saves_current_model(tmp_path: Path) -> None:
    session_id = "model-session-start"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    started = _run_hook_script(
        SESSION_START_HOOK,
        {
            "session_id": session_id,
            "transcript_path": str(tmp_path / "session.jsonl"),
            "source": "startup",
            "model": "gpt-5.6-codex",
        },
        env,
    )

    context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert context.count("[model-prompt-profile]") == 1
    assert "model=gpt-5.6-codex" in context
    assert "profile=gpt-5.6*" in context
    assert "catalog=static" in context
    assert "scope=session-fallback" in context
    assert state["active_model"] == "gpt-5.6-codex"
    assert state["active_prompt_profile"] == "gpt-5.6*"


def test_normal_user_prompt_emits_one_authoritative_selector_and_saves_model(tmp_path: Path) -> None:
    session_id = "normal-model-turn"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Review this change", "model": "gpt-5.6-sol"},
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert context.count("[model-prompt-profile]") == 1
    assert "model=gpt-5.6-sol" in context
    assert "scope=current-turn" in context
    assert "authoritative=true" in context
    assert "supersedes=all-prior" in context
    assert state["mode"] == "normal"
    assert state["active_model"] == "gpt-5.6-sol"
    assert state["active_prompt_profile"] == "gpt-5.6*"


@pytest.mark.parametrize("prompt", ["/redteam light", "/redteam off", "/opsec strict"])
def test_user_prompt_command_paths_emit_exactly_one_current_selector(tmp_path: Path, prompt: str) -> None:
    session_id = f"command-selector-{prompt.split()[-1]}"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": prompt, "model": "gpt-5.5-codex"},
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert context.count("[model-prompt-profile]") == 1
    assert "profile=gpt-5.5*" in context
    assert "scope=current-turn" in context
    assert state["active_model"] == "gpt-5.5-codex"
    assert state["active_prompt_profile"] == "gpt-5.5*"


def test_normal_turn_model_switch_replaces_the_session_selector(tmp_path: Path) -> None:
    session_id = "normal-model-switch"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    first = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "First", "model": "gpt-5.6-codex"},
        env,
    )
    second = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Second", "model": "gpt-5.4-codex"},
        env,
    )

    assert "profile=gpt-5.6*" in json.loads(first.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "profile=gpt-5.4*" in json.loads(second.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["active_model"] == "gpt-5.4-codex"
    assert state["active_prompt_profile"] == "gpt-5.4*"


def test_launcher_profile_lock_matches_profile_family_and_locks_default_exactly() -> None:
    assert model_prompt_profiles.is_pinned_model_compatible(
        "gpt-5.6-codex", "gpt-5.6-sol", "gpt-5.6*"
    )
    assert not model_prompt_profiles.is_pinned_model_compatible(
        "gpt-5.5-codex", "gpt-5.6-sol", "gpt-5.6*"
    )
    assert model_prompt_profiles.is_pinned_model_compatible("custom-a", "custom-a", "default")
    assert not model_prompt_profiles.is_pinned_model_compatible("custom-b", "custom-a", "default")


def test_launcher_profile_lock_blocks_incompatible_turn_without_mutating_state(tmp_path: Path) -> None:
    session_id = "launcher-profile-lock"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "CODEX_REDTEAM_PROFILE_MODE": "single",
        "CODEX_REDTEAM_PINNED_MODEL": "gpt-5.6-sol",
        "CODEX_REDTEAM_PINNED_PROFILE": "gpt-5.6*",
        "CODEX_REDTEAM_PINNED_PROFILE_FILE": "Jailbreak.gpt-5.6.md",
        "NO_COLOR": "1",
    }

    compatible = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Compatible", "model": "gpt-5.6-codex"},
        env,
    )
    blocked = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Incompatible", "model": "gpt-5.5-codex"},
        env,
    )

    compatible_context = json.loads(compatible.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "catalog=single-profile" in compatible_context
    assert "profile=gpt-5.6*" in compatible_context
    blocked_payload = json.loads(blocked.stdout)
    assert blocked_payload["decision"] == "block"
    assert "锁定模型族" in blocked_payload["reason"]
    assert "locked model family" in blocked_payload["reason"]
    assert "hookSpecificOutput" not in blocked_payload
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert state["active_model"] == "gpt-5.6-codex"
    assert state["active_prompt_profile"] == "gpt-5.6*"


def test_prompt_hook_rejects_alias_only_payload(tmp_path: Path) -> None:
    session_id = "alias-payload-session"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"sessionId": session_id, "message": "/redteam light"},
        env,
    )

    assert submitted.stdout == ""
    assert not (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").exists()


@pytest.mark.parametrize("payload", ["not-an-object", ["not-an-object"], {"source": "startup"}])
def test_session_start_rejects_payload_without_official_session_id(tmp_path: Path, payload: object) -> None:
    env = {**os.environ, "CODEX_HOME": str(tmp_path / "codex-home"), "NO_COLOR": "1"}

    started = _run_hook_script(SESSION_START_HOOK, payload, env)

    assert started.stdout == ""


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I cannot assist with that request.", True),
        ("Need more evidence before confirming this issue.", False),
        (None, False),
        (123, False),
    ],
)
def test_refusal_detection_accepts_only_stop_message_text(message: object, expected: bool) -> None:
    assert refusal_backstop.message_has_refusal(message) is expected


def test_stop_hook_records_and_next_prompt_consumes_refusal_overlay(tmp_path: Path) -> None:
    session_id = "stop-refusal-session"
    turn_id = "turn-refusal-1"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }
    state_path = codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"

    _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "model": "test-model", "prompt": "/redteam light"},
        env,
    )
    stopped = _run_hook_script(
        STOP_HOOK,
        {
            "session_id": session_id,
            "turn_id": turn_id,
            "stop_hook_active": False,
            "last_assistant_message": "I cannot assist with that request.",
        },
        env,
    )

    assert json.loads(stopped.stdout) == {}
    recorded = json.loads(state_path.read_text(encoding="utf-8"))
    assert recorded["pending_refusal_overlay"] is True
    assert recorded["last_refusal_turn_id"] == turn_id

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "model": "test-model", "prompt": "Review authentication controls"},
        env,
    )
    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[backstop:recent-refusal-detected]" in context
    consumed = json.loads(state_path.read_text(encoding="utf-8"))
    assert consumed["pending_refusal_overlay"] is False
    assert consumed["last_refusal_turn_id"] == turn_id
    assert consumed["active_model"] == "test-model"

    repeated = _run_hook_script(
        STOP_HOOK,
        {
            "session_id": session_id,
            "turn_id": turn_id,
            "stop_hook_active": False,
            "last_assistant_message": "I cannot assist with that request.",
        },
        env,
    )
    assert json.loads(repeated.stdout) == {}
    assert json.loads(state_path.read_text(encoding="utf-8"))["pending_refusal_overlay"] is False

    next_prompt = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "model": "test-model", "prompt": "Review authorization controls"},
        env,
    )
    next_context = json.loads(next_prompt.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[backstop:recent-refusal-detected]" not in next_context


def test_stop_hook_ignores_active_continuation_and_invalid_messages(tmp_path: Path) -> None:
    session_id = "stop-noop-session"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}
    state_path = codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"

    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    for payload in (
        {
            "session_id": session_id,
            "turn_id": "turn-active",
            "stop_hook_active": True,
            "last_assistant_message": "I cannot assist with that request.",
        },
        {
            "session_id": session_id,
            "turn_id": "turn-null",
            "stop_hook_active": False,
            "last_assistant_message": None,
        },
        {
            "session_id": session_id,
            "turn_id": "turn-missing-flag",
            "last_assistant_message": "I cannot assist with that request.",
        },
    ):
        stopped = _run_hook_script(STOP_HOOK, payload, env)
        assert json.loads(stopped.stdout) == {}

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["pending_refusal_overlay"] is False
    assert state["last_refusal_turn_id"] == ""


def test_stop_hook_is_noop_in_normal_mode(tmp_path: Path) -> None:
    session_id = "normal-stop-session"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    stopped = _run_hook_script(
        STOP_HOOK,
        {
            "session_id": session_id,
            "turn_id": "normal-turn",
            "stop_hook_active": False,
            "last_assistant_message": "I cannot assist with that request.",
        },
        env,
    )

    assert json.loads(stopped.stdout) == {}
    assert not (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").exists()


def test_user_prompt_submit_does_not_guess_refusal_from_messages(tmp_path: Path) -> None:
    session_id = "messages-refusal-session"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }

    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    submitted = _run_hook_script(
        PROMPT_HOOK,
        {
            "session_id": session_id,
            "prompt": "Review authentication controls",
            "messages": [
                {"role": "assistant", "content": "I cannot assist with that request."},
            ],
        },
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[backstop:recent-refusal-detected]" not in context


@pytest.mark.parametrize(
    ("command", "expected_mode"),
    [
        ("/redteam on", "redteam-light"),
        ("/redteam light", "redteam-light"),
        ("/redteam full", "redteam-full"),
        ("/redteam off", "normal"),
        ("进入红队模式", "redteam-light"),
        ("开启红队模式", "redteam-light"),
        ("退出红队模式", "normal"),
        ("关闭红队模式", "normal"),
        ("enable red team mode", "redteam-light"),
        ("disable red team mode", "normal"),
        ("  /REDTEAM   LIGHT  ", "redteam-light"),
    ],
)
def test_mode_commands_require_the_entire_prompt(command: str, expected_mode: str) -> None:
    assert prompt_parser.parse_mode_command(command) == expected_mode


@pytest.mark.parametrize(
    "prompt",
    [
        "请解释 /redteam light 命令",
        "/redteam light 请分析登录接口",
        "文档中写着 /redteam off",
        "比较 /redteam full 与 /redteam off",
        "/redteam light /redteam off",
        "不要开启红队模式",
        "不要关闭红队模式",
        "The document says enable red team mode.",
        "Do not disable red team mode while testing.",
        "`/redteam off`",
        "/redteam light\n/redteam off",
    ],
)
def test_mode_command_mentions_are_not_commands(prompt: str) -> None:
    assert prompt_parser.parse_mode_command(prompt) is None


@pytest.mark.parametrize(
    ("command", "expected_level"),
    [
        ("/opsec strict", "strict"),
        ("/opsec balanced", "balanced"),
        ("  /OPSEC   STRICT  ", "strict"),
    ],
)
def test_opsec_commands_require_the_entire_prompt(command: str, expected_level: str) -> None:
    assert prompt_parser.parse_opsec_command(command) == expected_level


@pytest.mark.parametrize(
    "prompt",
    [
        "代码示例：`/opsec strict`",
        "/opsec balanced 后继续任务",
        "比较 /opsec strict 和 /opsec balanced",
        "do not run /opsec strict",
    ],
)
def test_opsec_command_mentions_are_not_commands(prompt: str) -> None:
    assert prompt_parser.parse_opsec_command(prompt) is None


def test_session_start_preserves_mode_on_resume_and_compact(tmp_path: Path) -> None:
    session_id = "resume-session"
    temp_dir = tmp_path / "temp"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }
    transcript = tmp_path / "sessions" / "current.jsonl"
    state_path = codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"

    _run_hook_script(
        SESSION_START_HOOK,
        {"session_id": session_id, "transcript_path": str(transcript), "source": "startup"},
        env,
    )
    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    assert json.loads(state_path.read_text(encoding="utf-8"))["mode"] == "redteam-light"

    for source in ("resume", "compact"):
        started = _run_hook_script(
            SESSION_START_HOOK,
            {"session_id": session_id, "transcript_path": str(transcript), "source": source},
            env,
        )
        started_context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Session mode restored (redteam-light)" in started_context
        assert SYSTEM_PROMPT in started_context
        assert DO_SPECIAL_PROMPT in started_context
        assert started_context.count("[prepoison:frame-lock]") == 1
        assert REVERSE_PROMPT in started_context
        assert json.loads(state_path.read_text(encoding="utf-8"))["mode"] == "redteam-light"

        routed = _run_hook_script(
            PROMPT_HOOK,
            {"session_id": session_id, "prompt": "Review authentication bypass risk in the login endpoint"},
            env,
        )
        routed_context = json.loads(routed.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "[mode:redteam-light]" in routed_context
        assert "[router:" in routed_context
        assert REVERSE_PROMPT not in routed_context

    cleared = _run_hook_script(
        SESSION_START_HOOK,
        {"session_id": session_id, "transcript_path": str(transcript), "source": "clear"},
        env,
    )
    cleared_context = json.loads(cleared.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Default is normal" in cleared_context
    assert "[prepoison:frame-lock]" not in cleared_context
    assert json.loads(state_path.read_text(encoding="utf-8"))["mode"] == "normal"
    after_clear = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Review authentication bypass risk", "model": "gpt-5.6-codex"},
        env,
    )
    after_clear_context = json.loads(after_clear.stdout)["hookSpecificOutput"]["additionalContext"]
    assert after_clear_context.count("[model-prompt-profile]") == 1
    assert "scope=current-turn" in after_clear_context


@pytest.mark.parametrize(
    ("command", "mode"),
    [("/redteam light", "redteam-light"), ("/redteam full", "redteam-full")],
)
def test_mode_enable_injects_prepoison_once(tmp_path: Path, command: str, mode: str) -> None:
    session_id = f"enable-{mode}"
    temp_dir = tmp_path / "temp"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }

    enabled = _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": command}, env)
    context = json.loads(enabled.stdout)["hookSpecificOutput"]["additionalContext"]

    assert f"Red-team mode enabled ({mode})" in context
    assert context.count("[prepoison:frame-lock]") == 1
    assert REVERSE_PROMPT in context
    assert json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(encoding="utf-8")
    )["mode"] == mode

    routed = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Review authentication bypass risk in the login endpoint"},
        env,
    )
    routed_context = json.loads(routed.stdout)["hookSpecificOutput"]["additionalContext"]
    assert f"[mode:{mode}]" in routed_context
    assert "[phase:web]" in routed_context
    assert "[router:auth-sec]" in routed_context


def test_mode_disable_describes_remaining_base_and_history_context(tmp_path: Path) -> None:
    session_id = "disable-session"
    temp_dir = tmp_path / "temp"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "NO_COLOR": "1",
    }

    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    disabled = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "/redteam off", "model": "gpt-5.6-codex"},
        env,
    )
    context = json.loads(disabled.stdout)["hookSpecificOutput"]["additionalContext"]

    assert "Structured red-team routing disabled" in context
    assert "base instruction.ctf.md profile" in context
    assert "previous task context remain active" in context
    assert "state file remains stored" in context
    assert "/clear" in context
    state_path = codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"
    assert state_path.exists()
    assert json.loads(state_path.read_text(encoding="utf-8"))["mode"] == "normal"
    after_disable = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "Review authentication bypass risk", "model": "gpt-5.6-codex"},
        env,
    )
    after_disable_context = json.loads(after_disable.stdout)["hookSpecificOutput"]["additionalContext"]
    assert after_disable_context.count("[model-prompt-profile]") == 1
    assert "scope=current-turn" in after_disable_context


def test_embedded_enable_command_keeps_normal_mode_with_a_selector(tmp_path: Path) -> None:
    session_id = "embedded-enable-session"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "请解释 /redteam light 命令"},
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(encoding="utf-8")
    )
    assert context.count("[model-prompt-profile]") == 1
    assert state["mode"] == "normal"


def test_embedded_disable_command_routes_without_disabling_active_mode(tmp_path: Path) -> None:
    session_id = "embedded-disable-session"
    codex_home = tmp_path / "codex-home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "CODEX_REDTEAM_AUTOMATION_MODE": "plan-only",
        "NO_COLOR": "1",
    }
    state_path = codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"

    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env)
    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "分析文档中出现的 /redteam off 字符串"},
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[mode:redteam-light]" in context
    assert "Structured red-team routing disabled" not in context
    assert json.loads(state_path.read_text(encoding="utf-8"))["mode"] == "redteam-light"


def test_embedded_opsec_command_keeps_normal_mode_with_a_selector(tmp_path: Path) -> None:
    session_id = "embedded-opsec-session"
    codex_home = tmp_path / "codex-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    submitted = _run_hook_script(
        PROMPT_HOOK,
        {"session_id": session_id, "prompt": "代码示例：`/opsec strict`"},
        env,
    )

    context = json.loads(submitted.stdout)["hookSpecificOutput"]["additionalContext"]
    state = json.loads(
        (codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json").read_text(encoding="utf-8")
    )
    assert context.count("[model-prompt-profile]") == 1
    assert state["mode"] == "normal"


def test_state_paths_use_codex_home_and_ignore_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("TEMP", str(tmp_path / "temp-a"))
    monkeypatch.setenv("TMP", str(tmp_path / "temp-a"))

    assert redteam_state.state_root() == codex_home / "redteam-mode" / "state"
    assert redteam_state.state_dir() == codex_home / "redteam-mode" / "state" / "sessions"
    assert redteam_state.memory_dir() == codex_home / "redteam-mode" / "state" / "memory"

    redteam_state.save_state(redteam_state.RedTeamState(mode="redteam-light"), session_id="stable-session")
    monkeypatch.setenv("TEMP", str(tmp_path / "temp-b"))
    monkeypatch.setenv("TMP", str(tmp_path / "temp-b"))

    assert redteam_state.load_state("stable-session").mode == "redteam-light"


def test_resume_hook_uses_codex_home_when_temp_changes(tmp_path: Path) -> None:
    session_id = "temp-change-session"
    codex_home = tmp_path / "codex-home"
    transcript = tmp_path / "sessions" / "current.jsonl"
    env_a = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "TEMP": str(tmp_path / "temp-a"),
        "TMP": str(tmp_path / "temp-a"),
        "NO_COLOR": "1",
    }
    env_b = {
        **env_a,
        "TEMP": str(tmp_path / "temp-b"),
        "TMP": str(tmp_path / "temp-b"),
    }

    _run_hook_script(
        SESSION_START_HOOK,
        {"session_id": session_id, "transcript_path": str(transcript), "source": "startup"},
        env_a,
    )
    _run_hook_script(PROMPT_HOOK, {"session_id": session_id, "prompt": "/redteam light"}, env_a)
    resumed = _run_hook_script(
        SESSION_START_HOOK,
        {"session_id": session_id, "transcript_path": str(transcript), "source": "resume"},
        env_b,
    )
    context = json.loads(resumed.stdout)["hookSpecificOutput"]["additionalContext"]

    assert "Session mode restored (redteam-light)" in context
    assert (
        codex_home / "redteam-mode" / "state" / "sessions" / f"{session_id}.json"
    ).exists()


def test_state_paths_fall_back_to_user_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr(redteam_state.Path, "home", classmethod(lambda cls: fake_home))

    assert redteam_state.state_dir() == fake_home / ".codex" / "redteam-mode" / "state" / "sessions"


def test_missing_session_id_does_not_create_global_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    redteam_state.save_state(redteam_state.default_state())
    assert not redteam_state.state_dir().exists()
    with pytest.raises(ValueError):
        redteam_state.state_path(None)

    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}
    submitted = _run_hook_script(PROMPT_HOOK, {"prompt": "/redteam light"}, env)
    assert submitted.stdout == ""
    assert not redteam_state.state_dir().exists()


def test_memory_paths_follow_codex_state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    memory_store.save_session_memory("memory-session", {"facts_confirmed": ["fact"]})
    memory_store.append_long_memory("memory-session", {"summary": "entry"})

    memory_root = codex_home / "redteam-mode" / "state" / "memory"
    assert (memory_root / "memory-session.json").exists()
    assert (memory_root / "memory-session.long.json").exists()
    assert memory_store.load_session_memory("")["facts_confirmed"] == []
    assert not (memory_root / "global.json").exists()


def test_uninstall_preserves_runtime_state_files(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--enable-custom-skill-dirs",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    state_file = codex_home / "redteam-mode" / "state" / "sessions" / "preserved.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('{"mode":"normal"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--uninstall",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert state_file.exists()
    assert "runtime session state and memory are preserved" in result.stdout
    assert str(codex_home / "redteam-mode" / "state") in result.stdout


def test_normal_session_start_does_not_run_explicit_refusal_backstop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = tmp_path / "sessions"
    previous = sessions / "previous.jsonl"
    current = sessions / "current.jsonl"
    sessions.mkdir(parents=True)
    previous.write_text(
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "I cannot assist with that."}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    current.write_text('{"type":"event_msg","payload":{}}\n', encoding="utf-8")
    os.utime(previous, (10, 10))
    os.utime(current, (20, 20))
    monkeypatch.setenv("CODEX_REDTEAM_BACKSTOP_MODE", "detect")
    assert refusal_backstop.session_start_backstop_messages("normal-session", str(current))
    env = {
        **os.environ,
        "TEMP": str(tmp_path / "temp"),
        "TMP": str(tmp_path / "temp"),
        "NO_COLOR": "1",
    }

    started = _run_hook_script(
        SESSION_START_HOOK,
        {"session_id": "normal-session", "transcript_path": str(current), "source": "startup"},
        env,
    )
    context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]

    assert "Default is normal" in context
    assert "[backstop]" not in context


def test_session_prompt_notice_excludes_phase_specific_prompts() -> None:
    notice = supplemental_prompts.build_prompt_chain_notice(CODEX_PATH, mode="redteam-light")

    assert notice == f"{SYSTEM_PROMPT}\n\n{DO_SPECIAL_PROMPT}"
    assert REVERSE_PROMPT not in notice


def test_redteam_mode_overlay_loads_reverse_prompt_only_for_active_modes() -> None:
    light = supplemental_prompts.build_redteam_mode_overlay(CODEX_PATH, "redteam-light")
    full = supplemental_prompts.build_redteam_mode_overlay(CODEX_PATH, "redteam-full")
    normal = supplemental_prompts.build_redteam_mode_overlay(CODEX_PATH, "normal")

    assert light == REVERSE_PROMPT
    assert full == light
    assert normal == ""


def test_reverse_prompt_overlay_is_loaded_only_for_reverse_phase() -> None:
    reverse = supplemental_prompts.build_prompt_overlay(CODEX_PATH, "reverse")
    web = supplemental_prompts.build_prompt_overlay(CODEX_PATH, "web")

    assert REVERSE_PROMPT[:300] in reverse
    assert REVERSE_PROMPT[:300] not in web


def test_merge_config_preserves_user_sections(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text(
        """
# user-owned config
model = "gpt-5"

[automation]
mode = "active"

[mcp_servers.ida-pro-mcp]
command = "ida-mcp"

[projects."/work/demo"]
trust_level = "trusted"
""".lstrip(),
        encoding="utf-8",
    )

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    merged = tomllib.loads(target.read_text(encoding="utf-8"))
    assert merged["model"] == "gpt-5"
    assert merged["model_instructions_file"] == install.SYSTEM_INSTRUCTIONS_CONFIG_VALUE
    assert merged["features"]["hooks"] is True
    assert merged["features"]["automation"] is True
    assert merged["automation"]["mode"] == "active"
    assert merged["automation"]["allow_restricted_actions"] is False
    assert merged["mcp_servers"]["ida-pro-mcp"]["command"] == "ida-mcp"
    assert merged["projects"]["/work/demo"]["trust_level"] == "trusted"
    assert "# user-owned config" in target.read_text(encoding="utf-8")


def test_merge_config_does_not_put_automation_keys_in_skills_array(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text(
        """
[automation]
mode = "active"

[[skills.config]]
path = "/tmp/demo/SKILL.md"
enabled = false
""".lstrip(),
        encoding="utf-8",
    )

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    merged = tomllib.loads(target.read_text(encoding="utf-8"))
    assert merged["automation"]["allow_restricted_actions"] is False
    assert merged["automation"]["require_scope_for_network"] is True
    assert "allow_restricted_actions" not in merged["skills"]["config"][0]
    assert "require_scope_for_network" not in merged["skills"]["config"][0]


def test_merge_config_supports_quoted_automation_table(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text(
        """
["automation"]
mode = "active"
""".lstrip(),
        encoding="utf-8",
    )

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    merged = tomllib.loads(target.read_text(encoding="utf-8"))
    assert merged["automation"]["mode"] == "active"
    assert merged["automation"]["allow_restricted_actions"] is False


def test_merge_config_accepts_utf8_bom(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_bytes(b"\xef\xbb\xbf[automation]\nmode = \"active\"\n")

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    merged = tomllib.loads(target.read_text(encoding="utf-8"))
    assert merged["automation"]["mode"] == "active"
    assert merged["model_instructions_file"] == install.SYSTEM_INSTRUCTIONS_CONFIG_VALUE


def test_runtime_accepts_unchanged_utf8_bom_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    target = codex_home / "config.toml"
    target.parent.mkdir(parents=True)
    original = b"\xef\xbb\xbf" + (REPO_ROOT / "config.toml").read_bytes()
    target.write_bytes(original)

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    assert target.read_bytes() == original
    monkeypatch.setattr(controller.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.delenv("CODEX_REDTEAM_AUTOMATION_MODE", raising=False)
    monkeypatch.delenv("CODEX_REDTEAM_CONFIG", raising=False)
    assert controller._automation_mode_from_config(codex_home, "redteam-light") == "active"


def test_validate_config_accepts_utf8_bom(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_bytes(b"\xef\xbb\xbf" + (REPO_ROOT / "config.toml").read_bytes())

    _, messages = validate.validate_install(tmp_path)

    assert "config.toml: valid" in messages


def test_validate_config_rejects_invalid_toml(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("[automation\n", encoding="utf-8")

    all_ok, messages = validate.validate_install(tmp_path)

    assert all_ok is False
    assert any(message.startswith("config.toml: INVALID TOML") for message in messages)


def test_merge_config_backs_up_existing_file_before_change(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    original = '[automation]\nmode = "active"\n'
    target.write_text(original, encoding="utf-8")

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    backups = list(tmp_path.glob("config.toml.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == original
    assert tomllib.loads(target.read_text(encoding="utf-8"))["features"]["hooks"] is True


def test_merge_config_dry_run_does_not_write_or_backup(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    original = '[automation]\nmode = "active"\n'
    target.write_text(original, encoding="utf-8")

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=True)

    assert target.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("config.toml.*.bak")) == []


def test_merge_config_does_not_backup_when_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text((REPO_ROOT / "config.toml").read_text(encoding="utf-8"), encoding="utf-8")

    install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    assert list(tmp_path.glob("config.toml.*.bak")) == []


def test_merge_config_invalid_existing_toml_does_not_backup_or_write(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    original = "[automation\nmode = \"active\"\n"
    target.write_text(original, encoding="utf-8")

    with pytest.raises(TomlParseError):
        install.merge_config_file(REPO_ROOT / "config.toml", target, dry_run=False)

    assert target.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("config.toml.*.bak")) == []


def test_uninstall_config_plan_removes_only_unchanged_installer_values(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    config = codex_home / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        """
# user-owned config
[automation]
mode = "active"
user_setting = "keep"
""".lstrip(),
        encoding="utf-8",
    )

    merge_plan = install.prepare_config_merge(REPO_ROOT / "config.toml", config)
    install.apply_config_merge(merge_plan, dry_run=False)
    merged = config.read_text(encoding="utf-8").replace("hooks = true", "hooks = false")
    config.write_text(merged, encoding="utf-8")

    removal_plan = install.prepare_config_removal(codex_home, {"config_merge": merge_plan[3]})
    install.apply_config_removal(removal_plan, dry_run=False)

    remaining = tomllib.loads(config.read_text(encoding="utf-8"))
    assert "model_instructions_file" not in remaining
    assert remaining["features"]["hooks"] is False
    assert remaining["automation"] == {"mode": "active", "user_setting": "keep"}
    assert removal_plan[3] is False


def test_config_ownership_survives_idempotent_reinstall(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    config = codex_home / "config.toml"

    first = install.prepare_config_merge(REPO_ROOT / "config.toml", config)
    install.apply_config_merge(first, dry_run=False)
    second = install.prepare_config_merge(REPO_ROOT / "config.toml", config, first[3])
    install.apply_config_merge(second, dry_run=False)

    owned_paths = {tuple(entry["path"]) for entry in second[3]["added_values"]}
    assert ("model_instructions_file",) in owned_paths
    assert second[3]["existed_before"] is False

    removal = install.prepare_config_removal(codex_home, {"config_merge": second[3]})
    install.apply_config_removal(removal, dry_run=False)

    if config.exists():
        assert "model_instructions_file" not in tomllib.loads(config.read_text(encoding="utf-8"))


def test_uninstall_legacy_manifest_preserves_referenced_instruction(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    codex_home.mkdir(parents=True)
    config = codex_home / "config.toml"
    config.write_text("model_instructions_file = './instruction.ctf.md'\n", encoding="utf-8")
    instruction = codex_home / "instruction.ctf.md"
    instruction.write_text("managed instruction\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    manifest.write_text(json.dumps({"managed_paths": [str(instruction)]}), encoding="utf-8")

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert instruction.exists()
    assert config.exists()
    assert not manifest.exists()


def test_uninstall_invalid_config_fails_before_deleting_managed_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    codex_home.mkdir(parents=True)
    config = codex_home / "config.toml"
    config.write_text("[automation\n", encoding="utf-8")
    instruction = codex_home / "instruction.ctf.md"
    instruction.write_text("managed instruction\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    manifest.write_text(json.dumps({"managed_paths": [str(instruction)]}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert result.returncode != 0
    assert config.exists()
    assert instruction.exists()
    assert manifest.exists()


def test_install_invalid_existing_toml_fails_before_writes_or_cleanup(tmp_path: Path) -> None:
    codex_home = tmp_path / "custom-codex"
    agents_home = tmp_path / "custom-agents"
    codex_home.mkdir()
    original = "[automation\nmode = \"active\"\n"
    (codex_home / "config.toml").write_text(original, encoding="utf-8")
    stale = codex_home / "stale-managed.txt"
    stale.write_text("old managed file\n", encoding="utf-8")
    manifest = codex_home / "redteam-install-manifest.json"
    manifest.write_text(json.dumps({"managed_paths": [str(stale)]}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert result.returncode != 0
    assert (codex_home / "config.toml").read_text(encoding="utf-8") == original
    assert list(codex_home.glob("config.toml.*.bak")) == []
    assert not (codex_home / "instruction.ctf.md").exists()
    assert not (codex_home / "hooks").exists()
    assert not (codex_home / "AGENTS.md").exists()
    assert not agents_home.exists()
    assert stale.exists()
    assert manifest.exists()


def test_merge_hooks_json_accepts_utf8_bom_and_preserves_user_hooks(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    hooks_path = codex_home / "hooks.json"
    user_payload = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "user-command",
                            "statusMessage": "User hook",
                        }
                    ],
                }
            ]
        }
    }
    hooks_path.write_bytes(b"\xef\xbb\xbf" + json.dumps(user_payload).encode("utf-8"))

    install.merge_hooks_json(REPO_ROOT, codex_home, dry_run=False)

    merged = json.loads(hooks_path.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entries in merged["hooks"].values()
        for entry in entries
        for hook in entry["hooks"]
    ]
    assert "user-command" in commands
    assert any("session-start-context.py" in command for command in commands)
    assert any("stop-refusal-hook.py" in command for command in commands)


def test_validator_accepts_utf8_bom_hooks_json(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}
    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--enable-custom-skill-dirs",
        ],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )
    hooks_path = codex_home / "hooks.json"
    hooks_path.write_bytes(b"\xef\xbb\xbf" + hooks_path.read_bytes())

    all_ok, messages = validate.validate_install(codex_home)

    assert all_ok is True
    assert any(message.startswith("hooks.json: valid") for message in messages)


@pytest.mark.skipif(os.name != "nt", reason="commandWindows is executed by cmd.exe")
def test_installed_hook_commands_support_windows_shell_metacharacters(tmp_path: Path) -> None:
    special_name = "home & (qa) ! ^ %TEMP% ' 中文 with spaces"
    codex_home = tmp_path / f"codex {special_name}"
    agents_home = tmp_path / f"agents {special_name}"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "NO_COLOR": "1",
        "PYTHONIOENCODING": "cp1252",
    }

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--enable-custom-skill-dirs",
        ],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )

    hooks_payload = json.loads((codex_home / "hooks.json").read_text(encoding="utf-8"))
    session_hook = hooks_payload["hooks"]["SessionStart"][0]["hooks"][0]
    prompt_hook = hooks_payload["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    stop_hook = hooks_payload["hooks"]["Stop"][0]["hooks"][0]
    assert "-EncodedCommand" in session_hook["commandWindows"]
    assert "-EncodedCommand" in prompt_hook["commandWindows"]
    assert "-EncodedCommand" in stop_hook["commandWindows"]
    assert str(codex_home) not in session_hook["commandWindows"]
    assert str(codex_home) not in prompt_hook["commandWindows"]
    assert str(codex_home) not in stop_hook["commandWindows"]

    session_id = "space-path-session"
    started = subprocess.run(
        session_hook["commandWindows"],
        input=json.dumps({"session_id": session_id, "source": "startup"}),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert started.returncode == 0, started.stderr
    assert "Default is normal" in json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]

    enabled = subprocess.run(
        prompt_hook["commandWindows"],
        input=json.dumps({"session_id": session_id, "prompt": "/redteam light"}),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert enabled.returncode == 0, enabled.stderr
    assert "Red-team mode enabled" in json.loads(enabled.stdout)["hookSpecificOutput"]["additionalContext"]

    stopped = subprocess.run(
        stop_hook["commandWindows"],
        input=json.dumps(
            {
                "session_id": session_id,
                "turn_id": "windows-stop-turn",
                "stop_hook_active": False,
                "last_assistant_message": None,
            }
        ),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert stopped.returncode == 0, stopped.stderr
    assert json.loads(stopped.stdout) == {}


@pytest.mark.skipif(os.name == "nt", reason="POSIX hook command is executed by /bin/sh")
def test_installed_hook_commands_support_posix_shell_metacharacters(tmp_path: Path) -> None:
    special_name = "home & (qa) ! ^ $HOME ' 中文 with spaces"
    codex_home = tmp_path / f"codex {special_name}"
    agents_home = tmp_path / f"agents {special_name}"
    env = {**os.environ, "CODEX_HOME": str(codex_home), "NO_COLOR": "1"}

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--enable-custom-skill-dirs",
        ],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )

    hooks_payload = json.loads((codex_home / "hooks.json").read_text(encoding="utf-8"))
    session_command = hooks_payload["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    prompt_command = hooks_payload["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    stop_command = hooks_payload["hooks"]["Stop"][0]["hooks"][0]["command"]
    session_id = "posix-special-path-session"

    started = subprocess.run(
        session_command,
        input=json.dumps({"session_id": session_id, "source": "startup"}),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert started.returncode == 0, started.stderr
    assert "Default is normal" in json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]

    enabled = subprocess.run(
        prompt_command,
        input=json.dumps({"session_id": session_id, "prompt": "/redteam light"}),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert enabled.returncode == 0, enabled.stderr
    assert "Red-team mode enabled" in json.loads(enabled.stdout)["hookSpecificOutput"]["additionalContext"]

    stopped = subprocess.run(
        stop_command,
        input=json.dumps(
            {
                "session_id": session_id,
                "turn_id": "posix-stop-turn",
                "stop_hook_active": False,
                "last_assistant_message": None,
            }
        ),
        text=True,
        shell=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert stopped.returncode == 0, stopped.stderr
    assert json.loads(stopped.stdout) == {}


@pytest.mark.parametrize(
    "hooks_bytes",
    [
        b"{invalid json",
        json.dumps({"hooks": []}).encode("utf-8"),
    ],
)
@pytest.mark.parametrize("extra_args", [(), ("--dry-run",)])
def test_install_invalid_hooks_fails_before_writes_or_cleanup(
    tmp_path: Path,
    hooks_bytes: bytes,
    extra_args: tuple[str, ...],
) -> None:
    codex_home = tmp_path / "custom-codex"
    agents_home = tmp_path / "custom-agents"
    codex_home.mkdir()
    hooks_path = codex_home / "hooks.json"
    hooks_path.write_bytes(hooks_bytes)
    stale = codex_home / "stale-managed.txt"
    stale.write_text("old managed file\n", encoding="utf-8")
    manifest = codex_home / "redteam-install-manifest.json"
    manifest.write_text(json.dumps({"managed_paths": [str(stale)]}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            *extra_args,
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert result.returncode != 0
    assert hooks_path.read_bytes() == hooks_bytes
    assert stale.exists()
    assert manifest.exists()
    assert not (codex_home / "config.toml").exists()
    assert not (codex_home / "instruction.ctf.md").exists()
    assert not (codex_home / "AGENTS.md").exists()
    assert not (codex_home / "hooks").exists()
    assert not agents_home.exists()


def test_uninstall_invalid_hooks_fails_before_deleting_managed_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    codex_home.mkdir(parents=True)
    hooks_path = codex_home / "hooks.json"
    hooks_path.write_text("{invalid json", encoding="utf-8")
    managed = codex_home / "instruction.ctf.md"
    managed.write_text("managed\n", encoding="utf-8")
    manifest = codex_home / "redteam-install-manifest.json"
    manifest.write_text(json.dumps({"managed_paths": [str(managed)]}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert result.returncode != 0
    assert hooks_path.exists()
    assert managed.exists()
    assert manifest.exists()


def test_upgrade_cleanup_preserves_config_from_previous_manifest(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    agents_home = tmp_path / ".agents"
    codex_home.mkdir()
    config = codex_home / "config.toml"
    instruction = codex_home / "instruction.ctf.md"
    config.write_text("[automation]\nmode = \"active\"\n", encoding="utf-8")
    instruction.write_text("managed instruction\n", encoding="utf-8")
    install.manifest_path(codex_home).write_text(
        json.dumps(
            {
                "managed_paths": [
                    str(config),
                    str(instruction),
                ]
            }
        ),
        encoding="utf-8",
    )

    install._SAFE_ROOTS.clear()
    install._SAFE_ROOTS.extend([codex_home, agents_home, REPO_ROOT])

    install.upgrade_cleanup(codex_home, agents_home, codex_home / "AGENTS.md", [], dry_run=False)

    assert config.exists()
    assert not instruction.exists()
    assert install.manifest_path(codex_home).exists()


def test_manifest_tracks_config_as_merged_file(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    managed = [codex_home / "instruction.ctf.md"]
    agents_file = tmp_path / "AGENTS.md"

    agents_home = tmp_path / ".agents"
    install.write_manifest(
        codex_home,
        agents_file,
        agents_home,
        managed,
        codex_home / "logs" / "codex-redteam",
        False,
        dry_run=False,
    )

    payload = json.loads(install.manifest_path(codex_home).read_text(encoding="utf-8"))
    assert str(codex_home / "config.toml") not in payload["managed_paths"]
    assert str(codex_home / "config.toml") in payload["merged_files"]
    assert str(agents_file) in payload["merged_files"]
    assert payload["skills_paths"]["skills_root"] == str(agents_home / "skills")
    assert payload["custom_skill_dirs_enabled"] is False
    assert payload["log_root"] == str(codex_home / "logs" / "codex-redteam")
    assert payload["manifest_schema_version"] == 2
    assert payload["prompt_ownership_version"] == install.PROMPT_OWNERSHIP_VERSION
    assert payload["config_merge"]["path"] == str(codex_home / "config.toml")


def test_project_home_resolves_dot_codex_and_dot_agents(tmp_path: Path) -> None:
    project = tmp_path / "project"

    codex_home, agents_home, agents_file = install.resolve_install_paths(str(project), None, None)

    assert codex_home == project / ".codex"
    assert agents_home == project / ".agents"
    assert agents_file == project / "AGENTS.md"


def test_project_home_allows_custom_agents_home(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"

    codex_home, agents_home, agents_file = install.resolve_install_paths(
        str(project),
        None,
        str(custom_agents),
    )

    assert codex_home == project / ".codex"
    assert agents_home == custom_agents
    assert agents_file == project / "AGENTS.md"


def test_relative_install_paths_are_resolved_before_manifest_and_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    agents_home = tmp_path / "shared-agents"
    log_root = tmp_path / "logs"

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            "project",
            "--agents-home",
            "shared-agents",
            "--log-root",
            "logs",
            "--enable-custom-skill-dirs",
        ],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    codex_home = project / ".codex"
    payload = json.loads((codex_home / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    recorded_paths = [
        *payload["managed_paths"],
        *payload["merged_files"],
        payload["skills_paths"]["skills_root"],
        *payload["skills_paths"]["skill_dirs"],
        payload["log_root"],
    ]
    assert all(Path(path).is_absolute() for path in recorded_paths)
    assert payload["skills_paths"]["skills_root"] == str(agents_home / "skills")
    assert payload["log_root"] == str(log_root)

    hooks_payload = json.loads((codex_home / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entries in hooks_payload["hooks"].values()
        for entry in entries
        for hook in entry["hooks"]
    ]
    assert all(str(codex_home / "hooks") in command for command in commands)

    monkeypatch.chdir(project)
    assert runtime_paths.resolve_log_root(codex_home) == log_root
    assert skill_card.resolve_skills_dir(codex_home) == agents_home / "skills"


def test_relative_codex_home_environment_is_resolved_for_install(tmp_path: Path) -> None:
    env = {**os.environ, "CODEX_HOME": "profile"}

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--agents-home", "agents"],
        cwd=tmp_path,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    codex_home = tmp_path / "profile"
    payload = json.loads((codex_home / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["log_root"] == str(codex_home / "logs" / "codex-redteam")
    assert payload["skills_paths"]["skills_root"] == str(tmp_path / "agents" / "skills")
    assert all(Path(path).is_absolute() for path in payload["managed_paths"])


def test_relative_manifest_targets_are_rejected_as_a_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    agents_home = tmp_path / ".agents"
    codex_home.mkdir()
    relative_user_file = tmp_path / "user-owned.txt"
    relative_user_file.write_text("user data\n", encoding="utf-8")
    current_target = codex_home / "instruction.ctf.md"
    current_target.write_text("managed\n", encoding="utf-8")
    install.manifest_path(codex_home).write_text(
        json.dumps({"managed_paths": ["user-owned.txt", str(current_target)]}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(install, "_SAFE_ROOTS", [codex_home, agents_home, tmp_path])

    with pytest.raises(install.ManifestValidationError, match="must be absolute"):
        install.upgrade_cleanup(
            codex_home,
            agents_home,
            codex_home / "AGENTS.md",
            [current_target],
            dry_run=False,
        )

    assert relative_user_file.exists()
    assert current_target.exists()
    assert install.manifest_path(codex_home).exists()


@pytest.mark.parametrize(
    "manifest_text",
    ["{invalid json", "[]", "{}", '{"managed_paths":"not-a-list"}'],
)
def test_invalid_existing_manifest_fails_before_install_changes(tmp_path: Path, manifest_text: str) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    codex_home.mkdir()
    manifest = install.manifest_path(codex_home)
    manifest.write_text(manifest_text, encoding="utf-8")
    marker = codex_home / "user-marker.txt"
    marker.write_text("keep\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--codex-home", str(codex_home), "--agents-home", str(agents_home)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "invalid install manifest" in result.stderr
    assert manifest.read_text(encoding="utf-8") == manifest_text
    assert marker.read_text(encoding="utf-8") == "keep\n"
    assert not (codex_home / "instruction.ctf.md").exists()
    assert not (codex_home / "hooks").exists()
    assert not agents_home.exists()


def test_validation_failure_keeps_previous_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    codex_home.mkdir()
    stale = codex_home / "stale-managed.txt"
    stale.write_text("stale\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    original = json.dumps({"managed_paths": [str(stale)]})
    manifest.write_text(original, encoding="utf-8")

    def fail_validation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("validation failed")

    monkeypatch.setattr(install, "run_validate", fail_validation)
    monkeypatch.setattr(
        sys,
        "argv",
        [str(INSTALL_PATH), "--codex-home", str(codex_home), "--agents-home", str(agents_home)],
    )

    with pytest.raises(RuntimeError, match="validation failed"):
        install.main()

    assert manifest.read_text(encoding="utf-8") == original
    assert not manifest.with_name(f"{manifest.name}.tmp").exists()
    transaction = install.transaction_path(codex_home)
    transaction_data = json.loads(transaction.read_text(encoding="utf-8"))
    assert transaction_data["state"] == "validation_failed"
    assert transaction_data["previous_manifest"] == json.loads(original)
    assert transaction_data["candidate_manifest"]["version"] == install.APP_VERSION


def test_retry_reconciles_pending_transaction_and_commits_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    codex_home.mkdir()
    stale = codex_home / "stale-managed.txt"
    stale.write_text("stale\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    manifest.write_text(json.dumps({"managed_paths": [str(stale)]}), encoding="utf-8")
    argv = [str(INSTALL_PATH), "--codex-home", str(codex_home), "--agents-home", str(agents_home)]
    original_run_validate = install.run_validate

    def fail_validation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("validation failed")

    monkeypatch.setattr(install, "run_validate", fail_validation)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(RuntimeError, match="validation failed"):
        install.main()

    transaction = install.transaction_path(codex_home)
    assert transaction.exists()
    assert (agents_home / "skills" / "redteam-cve-validation" / "SKILL.md").exists()

    monkeypatch.setattr(install, "run_validate", original_run_validate)
    install.main()

    assert not transaction.exists()
    committed = json.loads(manifest.read_text(encoding="utf-8"))
    assert committed["version"] == install.APP_VERSION
    assert str(agents_home / "skills" / "redteam-cve-validation") in committed["managed_paths"]


def test_uninstall_cleans_previous_and_pending_candidate_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    codex_home.mkdir()
    previous_target = codex_home / "old-managed.txt"
    previous_target.write_text("old\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    manifest.write_text(json.dumps({"managed_paths": [str(previous_target)]}), encoding="utf-8")
    argv = [str(INSTALL_PATH), "--codex-home", str(codex_home), "--agents-home", str(agents_home)]

    def fail_validation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("validation failed")

    monkeypatch.setattr(install, "run_validate", fail_validation)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(RuntimeError, match="validation failed"):
        install.main()

    candidate_skill = agents_home / "skills" / "redteam-cve-validation" / "SKILL.md"
    assert candidate_skill.exists()
    assert install.transaction_path(codex_home).exists()

    install._SAFE_ROOTS.clear()
    install._SAFE_ROOTS.extend([codex_home, agents_home, REPO_ROOT])
    install.uninstall(REPO_ROOT, codex_home, agents_home, codex_home / "AGENTS.md", dry_run=False)

    assert not candidate_skill.exists()
    assert not manifest.exists()
    assert not install.transaction_path(codex_home).exists()


def test_invalid_pending_transaction_fails_before_install_changes(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    codex_home.mkdir()
    marker = codex_home / "user-marker.txt"
    marker.write_text("keep\n", encoding="utf-8")
    install.transaction_path(codex_home).write_text("{invalid json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--codex-home", str(codex_home), "--agents-home", str(agents_home)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "invalid install transaction" in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep\n"
    assert not (codex_home / "instruction.ctf.md").exists()
    assert not agents_home.exists()


def test_project_home_install_writes_under_dot_dirs(tmp_path: Path) -> None:
    project = tmp_path / "project"

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert (project / ".codex" / "config.toml").exists()
    assert (project / ".codex" / "redteam-mode" / "system-instructions.md").exists()
    assert (project / ".codex" / "redteam-mode" / "launcher.py").exists()
    assert (project / ".codex" / "redteam-mode" / "codex-redteam.cmd").exists()
    assert (project / ".codex" / "redteam-mode" / "codex-redteam").exists()
    assert not (project / ".codex" / "instruction.ctf.md").exists()
    assert (project / "AGENTS.md").exists()
    assert not (project / ".codex" / "AGENTS.md").exists()
    assert (project / ".agents" / "skills" / "redteam-cve-validation" / "SKILL.md").exists()
    assert not (project / "config.toml").exists()
    payload = json.loads((project / ".codex" / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["skills_paths"]["skills_root"] == str(project / ".agents" / "skills")
    assert str(project / ".agents" / "skills" / "redteam-cve-validation") in payload["skills_paths"]["skill_dirs"]
    assert payload["custom_skill_dirs_enabled"] is False
    assert payload["log_root"] == str(project / ".codex" / "logs" / "codex-redteam")


def test_prompt_seeds_track_only_installer_created_files_across_reinstall(tmp_path: Path) -> None:
    project = tmp_path / "project"
    prompts_dir = project / ".codex" / "prompts"
    prompts_dir.mkdir(parents=True)
    user_prompt = prompts_dir / "Reverse.md"
    user_prompt.write_text("user-owned prompt\n", encoding="utf-8")
    command = [sys.executable, str(INSTALL_PATH), "--project-home", str(project)]

    for _ in range(2):
        subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=subprocess.DEVNULL)
        payload = json.loads(
            (project / ".codex" / "redteam-install-manifest.json").read_text(encoding="utf-8")
        )
        assert str(prompts_dir / "do_special.md") in payload["managed_paths"]
        assert str(prompts_dir / "system-prompt.md") in payload["managed_paths"]
        assert str(user_prompt) not in payload["managed_paths"]
        assert user_prompt.read_text(encoding="utf-8") == "user-owned prompt\n"

    subprocess.run(
        [*command, "--uninstall"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert user_prompt.read_text(encoding="utf-8") == "user-owned prompt\n"
    assert not (prompts_dir / "do_special.md").exists()
    assert not (prompts_dir / "system-prompt.md").exists()


def test_upgrade_adopts_untracked_legacy_prompt_with_backup(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    prompts_dir = codex_home / "prompts"
    prompts_dir.mkdir(parents=True)
    legacy_prompt = prompts_dir / "Reverse.md"
    legacy_prompt.write_text("legacy prompt content\n", encoding="utf-8")
    install.manifest_path(codex_home).write_text(
        json.dumps(
            {
                "name": install.APP_NAME,
                "version": "1.2.0",
                "managed_paths": [],
            }
        ),
        encoding="utf-8",
    )
    command = [sys.executable, str(INSTALL_PATH), "--project-home", str(project)]

    subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=subprocess.DEVNULL)

    backups = list(prompts_dir.glob("Reverse.md.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "legacy prompt content\n"
    assert legacy_prompt.read_text(encoding="utf-8").strip() == REVERSE_PROMPT
    payload = json.loads(install.manifest_path(codex_home).read_text(encoding="utf-8"))
    assert str(legacy_prompt) in payload["managed_paths"]

    subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=subprocess.DEVNULL)

    assert len(list(prompts_dir.glob("Reverse.md.*.bak"))) == 1
    assert legacy_prompt.read_text(encoding="utf-8").strip() == REVERSE_PROMPT


def test_upgrade_builds_system_instructions_from_adopted_legacy_profiles(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    prompts_dir = codex_home / "prompts"
    prompts_dir.mkdir(parents=True)
    legacy_profile = prompts_dir / "Jailbreak.default.md"
    legacy_profile.write_text("legacy profile content\n", encoding="utf-8")
    install.manifest_path(codex_home).write_text(
        json.dumps(
            {
                "name": install.APP_NAME,
                "version": "1.2.0",
                "managed_paths": [],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    generated = (codex_home / "redteam-mode" / "system-instructions.md").read_text(
        encoding="utf-8"
    )
    metadata = json.loads(
        generated.split(install.SYSTEM_PROFILE_START, 1)[1]
        .split(install.SYSTEM_PROFILE_END, 1)[0]
        .strip()
    )
    bundled = (CODEX_PATH / "prompts" / "Jailbreak.default.md").read_text(
        encoding="utf-8-sig"
    ).strip()
    assert metadata["profile_sha256"] == install._sha256_text(bundled)
    assert metadata["profile_sha256"] != install._sha256_text("legacy profile content")


def test_upgrade_adopts_matching_untracked_legacy_prompt_without_backup(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    prompts_dir = codex_home / "prompts"
    prompts_dir.mkdir(parents=True)
    legacy_prompt = prompts_dir / "Reverse.md"
    legacy_prompt.write_bytes((CODEX_PATH / "prompts" / "Reverse.md").read_bytes())
    install.manifest_path(codex_home).write_text(
        json.dumps(
            {
                "name": install.APP_NAME,
                "version": "1.2.0",
                "managed_paths": [],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert not list(prompts_dir.glob("Reverse.md.*.bak"))
    assert legacy_prompt.read_text(encoding="utf-8").strip() == REVERSE_PROMPT
    payload = json.loads(install.manifest_path(codex_home).read_text(encoding="utf-8"))
    assert str(legacy_prompt) in payload["managed_paths"]


def test_upgrade_legacy_prompt_dry_run_only_reports_changes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    prompts_dir = codex_home / "prompts"
    prompts_dir.mkdir(parents=True)
    legacy_prompt = prompts_dir / "Reverse.md"
    legacy_prompt.write_text("legacy prompt content\n", encoding="utf-8")
    manifest = install.manifest_path(codex_home)
    manifest.write_text(
        json.dumps(
            {
                "name": install.APP_NAME,
                "version": "1.2.0",
                "managed_paths": [],
            }
        ),
        encoding="utf-8",
    )
    original_manifest = manifest.read_bytes()

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--dry-run"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "replace legacy prompt" in result.stdout
    assert "backup" in result.stdout
    assert legacy_prompt.read_text(encoding="utf-8") == "legacy prompt content\n"
    assert not list(prompts_dir.glob("Reverse.md.*.bak"))
    assert manifest.read_bytes() == original_manifest


def test_install_does_not_adopt_prompt_from_foreign_manifest(tmp_path: Path) -> None:
    project = tmp_path / "project"
    codex_home = project / ".codex"
    prompts_dir = codex_home / "prompts"
    prompts_dir.mkdir(parents=True)
    user_prompt = prompts_dir / "Reverse.md"
    user_prompt.write_text("user-owned prompt\n", encoding="utf-8")
    install.manifest_path(codex_home).write_text(
        json.dumps(
            {
                "name": "different-installer",
                "managed_paths": [],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert user_prompt.read_text(encoding="utf-8") == "user-owned prompt\n"
    assert not list(prompts_dir.glob("Reverse.md.*.bak"))
    payload = json.loads(install.manifest_path(codex_home).read_text(encoding="utf-8"))
    assert str(user_prompt) not in payload["managed_paths"]


def test_project_home_migrates_old_dot_codex_agents_block(tmp_path: Path) -> None:
    project = tmp_path / "project"
    old_agents = project / ".codex" / "AGENTS.md"
    old_agents.parent.mkdir(parents=True)
    old_agents.write_text(install.managed_agents_block(REPO_ROOT), encoding="utf-8")

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert (project / "AGENTS.md").exists()
    assert not old_agents.exists()


def test_project_home_uninstall_preserves_user_agents_content(tmp_path: Path) -> None:
    project = tmp_path / "project"
    agents_file = project / "AGENTS.md"

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    agents_file.write_text(
        "user guidance\n\n" + agents_file.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert agents_file.read_text(encoding="utf-8") == "user guidance\n"


def test_project_home_uninstall_removes_managed_config_reference(tmp_path: Path) -> None:
    project = tmp_path / "project"

    for _ in range(2):
        subprocess.run(
            [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    config = project / ".codex" / "config.toml"
    if config.exists():
        assert "model_instructions_file" not in tomllib.loads(config.read_text(encoding="utf-8"))
    assert not (project / ".codex" / "instruction.ctf.md").exists()


def test_project_home_install_accepts_custom_agents_home(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert (project / ".codex" / "config.toml").exists()
    assert (custom_agents / "skills" / "redteam-cve-validation" / "SKILL.md").exists()
    assert not (project / ".agents").exists()
    payload = json.loads((project / ".codex" / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["skills_paths"]["skills_root"] == str(custom_agents / "skills")
    assert str(custom_agents / "skills" / "redteam-cve-validation") in payload["skills_paths"]["skill_dirs"]


def test_custom_agents_home_without_runtime_opt_in_warns(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "[WARN] custom --agents-home" in result.stdout
    assert "--enable-custom-skill-dirs" in result.stdout


def test_custom_agents_home_with_runtime_opt_in_does_not_warn(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
            "--enable-custom-skill-dirs",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "[WARN] custom --agents-home" not in result.stdout


def test_validate_reports_custom_skill_runtime_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"
    fake_home = tmp_path / "home"
    runtime_skills = fake_home / ".agents" / "skills"
    _write_skill(runtime_skills)

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    monkeypatch.setattr(skill_card.Path, "home", classmethod(lambda cls: fake_home))

    all_ok, messages = validate.validate_install(project / ".codex")

    assert all_ok is True
    assert f"Installed skill cards: {custom_agents / 'skills'}" in messages
    assert f"Runtime skill cards: {runtime_skills}" in messages
    assert any("runtime is not using the installed skill root" in message for message in messages)


def test_uninstall_external_agents_home_requires_original_scope(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"
    codex_home = project / ".codex"

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    manifest = codex_home / "redteam-install-manifest.json"
    manifest_before = manifest.read_bytes()
    managed = codex_home / "redteam-mode" / "system-instructions.md"
    skill = custom_agents / "skills" / "redteam-cve-validation" / "SKILL.md"

    result = subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project), "--uninstall"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "outside the current cleanup scope" in result.stderr
    assert "--agents-home" in result.stderr
    assert manifest.read_bytes() == manifest_before
    assert managed.exists()
    assert skill.exists()

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(custom_agents),
            "--uninstall",
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert not manifest.exists()
    assert not managed.exists()
    assert not skill.exists()


def test_upgrade_external_agents_home_requires_original_scope(tmp_path: Path) -> None:
    project = tmp_path / "project"
    original_agents = tmp_path / "original-agents"
    replacement_agents = tmp_path / "replacement-agents"
    codex_home = project / ".codex"

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(original_agents),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    manifest = codex_home / "redteam-install-manifest.json"
    manifest_before = manifest.read_bytes()
    managed = codex_home / "redteam-mode" / "system-instructions.md"
    old_skill = original_agents / "skills" / "redteam-cve-validation" / "SKILL.md"

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--agents-home",
            str(replacement_agents),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "upgrade cleanup blocked" in result.stderr
    assert manifest.read_bytes() == manifest_before
    assert managed.exists()
    assert old_skill.exists()
    assert not replacement_agents.exists()


def test_install_manifest_records_custom_skill_dirs_and_log_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_log = tmp_path / "custom-logs"

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--enable-custom-skill-dirs",
            "--log-root",
            str(custom_log),
        ],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    payload = json.loads((project / ".codex" / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["custom_skill_dirs_enabled"] is True
    assert payload["log_root"] == str(custom_log)


def test_codex_home_install_manifest_log_root_follows_codex_home(tmp_path: Path) -> None:
    codex_home = tmp_path / "custom-codex"
    agents_home = tmp_path / "custom-agents"
    env = {**os.environ, "CODEX_HOME": str(codex_home)}

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--agents-home", str(agents_home)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        env=env,
    )

    payload = json.loads((codex_home / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["log_root"] == str(codex_home / "logs" / "codex-redteam")


def test_skill_resolver_ignores_agents_home_and_uses_project_dot_agents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    env_agents = tmp_path / "env-agents"
    _write_skill(project / ".agents" / "skills")
    _write_skill(env_agents / "skills")
    monkeypatch.setattr(skill_card.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("AGENTS_HOME", str(env_agents))

    resolved = skill_card.resolve_skills_dir(project / ".codex")

    assert resolved == project / ".agents" / "skills"


def test_skill_resolver_uses_custom_manifest_skills_root_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    custom_root = tmp_path / "custom-agents" / "skills"
    fake_home = tmp_path / "home"
    _write_skill(project / ".agents" / "skills")
    _write_skill(custom_root)
    manifest = project / ".codex" / "redteam-install-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "custom_skill_dirs_enabled": True,
                "skills_paths": {
                    "skills_root": str(custom_root),
                    "skill_dirs": [str(custom_root / "redteam-demo")],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_card.Path, "home", classmethod(lambda cls: fake_home))

    resolved = skill_card.resolve_skills_dir(project / ".codex")

    assert resolved == custom_root


def test_skill_resolver_falls_back_to_manifest_root_when_defaults_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    custom_root = tmp_path / "custom-agents" / "skills"
    fake_home = tmp_path / "home"
    _write_skill(custom_root)
    manifest = project / ".codex" / "redteam-install-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "custom_skill_dirs_enabled": False,
                "skills_paths": {
                    "skills_root": str(custom_root),
                    "skill_dirs": [str(custom_root / "redteam-demo")],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_card.Path, "home", classmethod(lambda cls: fake_home))

    resolved = skill_card.resolve_skills_dir(project / ".codex")

    assert resolved == custom_root


def test_runtime_log_root_comes_from_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    log_root = tmp_path / "custom-logs"
    fake_home = tmp_path / "home"
    manifest = project / ".codex" / "redteam-install-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"log_root": str(log_root)}), encoding="utf-8")
    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda cls: fake_home))

    resolved = runtime_paths.resolve_log_root(project / ".codex")

    assert resolved == log_root


def test_runtime_manifest_resolves_from_current_codex_dir_without_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "custom-codex"
    custom_root = tmp_path / "custom-agents" / "skills"
    log_root = tmp_path / "custom-logs"
    fake_home = tmp_path / "home"
    _write_skill(custom_root)
    manifest = codex_home / "redteam-install-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "log_root": str(log_root),
                "custom_skill_dirs_enabled": True,
                "skills_paths": {
                    "skills_root": str(custom_root),
                    "skill_dirs": [str(custom_root / "redteam-demo")],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr(skill_card.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.delenv("CODEX_HOME", raising=False)

    assert runtime_paths.resolve_log_root(codex_home) == log_root
    assert skill_card.resolve_skills_dir(codex_home) == custom_root


def test_runtime_log_root_falls_back_to_user_codex_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    fake_home = tmp_path / "home"
    monkeypatch.setattr(runtime_paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.delenv("CODEX_HOME", raising=False)

    resolved = runtime_paths.resolve_log_root(project / ".codex")

    assert resolved == fake_home / ".codex" / "logs" / "codex-redteam"


def test_extract_transcript_path_from_hook_payload() -> None:
    payload = {"transcript_path": "C:/tmp/session.jsonl"}

    assert prompt_parser.extract_transcript_path(payload) == "C:/tmp/session.jsonl"


def test_refusal_backstop_session_dir_uses_transcript_session_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = tmp_path / "sessions" / "2026" / "07" / "10" / "current.jsonl"
    fake_home = tmp_path / "home"
    monkeypatch.setattr(refusal_backstop.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("CODEX_REDTEAM_SESSION_DIR", str(tmp_path / "ignored"))

    resolved = refusal_backstop._session_dir(str(transcript))

    assert resolved == tmp_path / "sessions"


def test_refusal_backstop_session_dir_falls_back_to_transcript_parent(tmp_path: Path) -> None:
    transcript = tmp_path / "transcripts" / "current.jsonl"

    assert refusal_backstop._session_dir(str(transcript)) == transcript.parent


def test_refusal_backstop_selects_previous_session_across_date_directories(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    previous = _write_session(sessions / "2026" / "07" / "09" / "previous.jsonl", 10)
    current = _write_session(sessions / "2026" / "07" / "10" / "current.jsonl", 20)

    selected = refusal_backstop._select_previous_session(None, str(current))

    assert selected == previous


def test_refusal_backstop_selects_previous_session_on_same_day(tmp_path: Path) -> None:
    day = tmp_path / "sessions" / "2026" / "07" / "10"
    previous = _write_session(day / "previous.jsonl", 10)
    current = _write_session(day / "current.jsonl", 20)

    assert refusal_backstop._select_previous_session(None, str(current)) == previous


def test_refusal_backstop_selects_latest_other_file_when_current_is_missing(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    older = _write_session(sessions / "2026" / "07" / "09" / "older.jsonl", 10)
    latest = _write_session(sessions / "2026" / "07" / "10" / "latest.jsonl", 20)
    missing_current = sessions / "2026" / "07" / "11" / "current.jsonl"

    assert refusal_backstop._select_previous_session(None, str(missing_current)) == latest
    assert latest != older


def test_refusal_backstop_does_not_fall_back_to_another_profile(tmp_path: Path) -> None:
    custom_sessions = tmp_path / "custom" / "sessions"
    current = _write_session(custom_sessions / "2026" / "07" / "10" / "current.jsonl", 20)
    _write_session(tmp_path / "home" / ".codex" / "sessions" / "2026" / "07" / "09" / "global.jsonl", 10)

    assert refusal_backstop._select_previous_session(None, str(current)) is None


def test_refusal_backstop_session_dir_uses_codex_home_without_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    fake_home = tmp_path / "home"
    monkeypatch.setattr(patcher.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_REDTEAM_SESSION_DIR", str(tmp_path / "ignored"))

    resolved = refusal_backstop._session_dir()

    assert resolved == codex_home / "sessions"


def test_session_patcher_default_session_dir_uses_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    assert patcher.default_session_dir() == codex_home / "sessions"


def test_project_home_rejects_codex_home_mix(tmp_path: Path) -> None:
    project = tmp_path / "project"

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALL_PATH),
            "--project-home",
            str(project),
            "--codex-home",
            str(project / "custom-codex"),
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    assert result.returncode == 2

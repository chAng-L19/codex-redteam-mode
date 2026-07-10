from __future__ import annotations

import importlib.util
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
SKILL_CARD_PATH = REPO_ROOT / "codex" / "hooks" / "core" / "skill_card.py"

spec = importlib.util.spec_from_file_location("install_script", INSTALL_PATH)
install = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = install
assert spec.loader is not None
spec.loader.exec_module(install)

skill_spec = importlib.util.spec_from_file_location("skill_card_script", SKILL_CARD_PATH)
skill_card = importlib.util.module_from_spec(skill_spec)
sys.modules[skill_spec.name] = skill_card
assert skill_spec.loader is not None
skill_spec.loader.exec_module(skill_card)


def _write_skill(skills_root: Path, name: str = "redteam-demo") -> Path:
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(
        f"---\nname: {name}\ndescription: demo\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    return skill_dir


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
    assert merged["model_instructions_file"] == "./instruction.ctf.md"
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
    assert merged["model_instructions_file"] == "./instruction.ctf.md"


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
    assert not install.manifest_path(codex_home).exists()


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


def test_project_home_install_writes_under_dot_dirs(tmp_path: Path) -> None:
    project = tmp_path / "project"

    subprocess.run(
        [sys.executable, str(INSTALL_PATH), "--project-home", str(project)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    assert (project / ".codex" / "config.toml").exists()
    assert (project / ".codex" / "instruction.ctf.md").exists()
    assert (project / "AGENTS.md").exists()
    assert not (project / ".codex" / "AGENTS.md").exists()
    assert (project / ".agents" / "skills" / "redteam-cve-validation" / "SKILL.md").exists()
    assert not (project / "config.toml").exists()
    payload = json.loads((project / ".codex" / "redteam-install-manifest.json").read_text(encoding="utf-8"))
    assert payload["skills_paths"]["skills_root"] == str(project / ".agents" / "skills")
    assert str(project / ".agents" / "skills" / "redteam-cve-validation") in payload["skills_paths"]["skill_dirs"]
    assert payload["custom_skill_dirs_enabled"] is False
    assert payload["log_root"] == str(project / ".codex" / "logs" / "codex-redteam")


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

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PATH = REPO_ROOT / "scripts" / "install.py"

spec = importlib.util.spec_from_file_location("install_script", INSTALL_PATH)
install = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = install
assert spec.loader is not None
spec.loader.exec_module(install)


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

    with pytest.raises(tomllib.TOMLDecodeError):
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

    install.upgrade_cleanup(codex_home, agents_home, [], dry_run=False)

    assert config.exists()
    assert not instruction.exists()
    assert not install.manifest_path(codex_home).exists()


def test_manifest_tracks_config_as_merged_file(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    managed = [codex_home / "instruction.ctf.md"]

    install.write_manifest(codex_home, managed, dry_run=False)

    payload = json.loads(install.manifest_path(codex_home).read_text(encoding="utf-8"))
    assert str(codex_home / "config.toml") not in payload["managed_paths"]
    assert str(codex_home / "config.toml") in payload["merged_files"]


def test_project_home_resolves_dot_codex_and_dot_agents(tmp_path: Path) -> None:
    project = tmp_path / "project"

    codex_home, agents_home = install.resolve_install_homes(str(project), None, None)

    assert codex_home == project / ".codex"
    assert agents_home == project / ".agents"


def test_project_home_allows_custom_agents_home(tmp_path: Path) -> None:
    project = tmp_path / "project"
    custom_agents = tmp_path / "custom-agents"

    codex_home, agents_home = install.resolve_install_homes(
        str(project),
        None,
        str(custom_agents),
    )

    assert codex_home == project / ".codex"
    assert agents_home == custom_agents


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
    assert (project / ".agents" / "skills" / "redteam-cve-validation" / "SKILL.md").exists()
    assert not (project / "config.toml").exists()


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

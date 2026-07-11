#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-install validation script for codex-redteam-optin-mode.

Verifies that all required files were deployed correctly and the install
is functional.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import List, Tuple


REQUIRED_CODEX_FILES = [
    "hooks/session-start-context.py",
    "hooks/hook-security-context-hook.py",
    "hooks/redteam_state.py",
    "hooks/core/emitter.py",
    "hooks/core/phase_detector.py",
    "hooks/core/semantic_phase.py",
    "hooks/core/loop_engine.py",
    "hooks/core/supplemental_prompts.py",
    "hooks/core/controller.py",
    "hooks/core/verify_engine.py",
    "hooks/core/skill_card.py",
    "hooks/core/evidence_artifact.py",
    "hooks/core/taskbook.py",
    "hooks/core/doctrine.py",
    "router/__init__.py",
    "router/router_engine.py",
    "router/mappings.py",
    "router/pack_selector.py",
    "router/leaf_selector.py",
    "router/method_engine.py",
    "orchestrator/__init__.py",
    "orchestrator/planner.py",
    "orchestrator/state_graph.py",
    "orchestrator/artifacts.py",
    "orchestrator/gates.py",
    "orchestrator/task_schema.py",
    "automation/__init__.py",
    "automation/planner.py",
    "automation/artifact_store.py",
    "automation/decision_tree.py",
    "automation/executor.py",
    "automation/gate_engine.py",
    "automation/loop_recorder.py",
    "automation/loop_runtime.py",
    "automation/loop_state.py",
    "automation/quick_cards.py",
    "automation/report_gate.py",
    "automation/rhythm.py",
    "automation/scope_gate.py",
    "automation/tool_discovery.py",
    "automation/tool_registry.py",
    "session_patcher/__init__.py",
    "session_patcher/__main__.py",
    "session_patcher/cli.py",
    "session_patcher/detector.py",
    "session_patcher/patcher.py",
]

REQUIRED_ROOT_FILES = [
    "instruction.ctf.md",
    "config.toml",
]

OPTIONAL_CODEX_FILES = [
    "prompts/Reverse.md",
]

REQUIRED_SKILL_IDS = [
    "redteam-recon-intake",
    "redteam-cve-lookup",
    "redteam-cve-validation",
]


def _skill_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def check_skill_metadata(skill_md: Path, expected_name: str) -> Tuple[bool, str]:
    meta = _skill_frontmatter(skill_md)
    if not meta:
        return False, f"  FAIL {expected_name}/SKILL.md missing YAML frontmatter"
    if meta.get("name") != expected_name:
        return False, f"  FAIL {expected_name}/SKILL.md name mismatch: {meta.get('name')!r}"
    if not meta.get("description"):
        return False, f"  FAIL {expected_name}/SKILL.md missing description"
    return True, f"  OK  {expected_name}/SKILL.md metadata"


def _codex_root(codex_home: Path) -> Path:
    """Accept either an installed Codex home or this repository root."""
    if (codex_home / "hooks").exists():
        return codex_home
    if (codex_home / "codex" / "hooks").exists():
        return codex_home / "codex"
    return codex_home


def check_file(codex_root: Path, relative: str) -> Tuple[bool, str]:
    path = codex_root / relative
    if path.exists():
        return True, f"  OK  {relative}"
    return False, f"  MISS {relative}"


def _manifest_skill_dir(repo_root: Path, manifest_override: Path | None = None) -> Path | None:
    manifest = manifest_override or repo_root / "redteam-install-manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for raw in data.get("managed_paths", []):
        try:
            path = Path(raw)
        except TypeError:
            continue
        if path.name in REQUIRED_SKILL_IDS and path.parent.name == "skills":
            return path.parent
    return None


def _manifest_merged_file(codex_home: Path, filename: str, manifest_override: Path | None = None) -> Path | None:
    manifest = manifest_override or codex_home / "redteam-install-manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for raw in data.get("merged_files", []):
        try:
            path = Path(raw)
        except TypeError:
            continue
        if path.name == filename:
            return path
    return None


def _resolve_skills_dir(repo_root: Path, source_tree_mode: bool, manifest_override: Path | None = None) -> Path | None:
    repo_skills = repo_root / "agents" / "skills"
    if repo_skills.exists():
        return repo_skills
    manifest_skills = _manifest_skill_dir(repo_root, manifest_override)
    if manifest_skills and manifest_skills.exists():
        return manifest_skills
    default_agents = Path.home() / ".agents" / "skills"
    if not source_tree_mode and default_agents.exists():
        return default_agents
    return None


def _resolve_runtime_skills_dir(codex_root: Path, source_tree_mode: bool) -> Path | None:
    if source_tree_mode:
        return None
    hooks_dir = codex_root / "hooks"
    hooks_dir_str = str(hooks_dir)
    if hooks_dir_str not in sys.path:
        sys.path.insert(0, hooks_dir_str)
    try:
        from core.skill_card import resolve_skills_dir
    except ImportError:
        return None
    return resolve_skills_dir(codex_root)


def validate_install(codex_home: Path, manifest_override: Path | None = None) -> Tuple[bool, List[str]]:
    messages: List[str] = []
    all_ok = True

    codex_root = _codex_root(codex_home)
    repo_root = codex_root.parent if codex_root.name == "codex" else codex_home
    source_tree_mode = codex_root.name == "codex" and (repo_root / "scripts" / "install.py").exists()

    messages.append(f"Validating codex-redteam installation at: {codex_home}")
    messages.append(f"Resolved codex root: {codex_root}")
    messages.append("")

    messages.append("Required files:")
    for rel in REQUIRED_CODEX_FILES:
        ok, msg = check_file(codex_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False
    for rel in REQUIRED_ROOT_FILES:
        ok, msg = check_file(repo_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False

    messages.append("")
    messages.append("Optional files:")
    for rel in OPTIONAL_CODEX_FILES:
        ok, msg = check_file(codex_root, rel)
        if not ok:
            msg = msg.replace("MISS", "WARN (optional)")
        messages.append(msg)

    hooks_path = repo_root / "hooks.json"
    if hooks_path.exists():
        try:
            data = json.loads(hooks_path.read_text(encoding="utf-8-sig"))
            hooks_root = data.get("hooks", {})
            hook_count = sum(
                len(entries) for entries in hooks_root.values()
            )
            messages.append("")
            messages.append(f"hooks.json: valid ({hook_count} hook event groups)")
        except (json.JSONDecodeError, OSError) as e:
            messages.append("")
            messages.append(f"hooks.json: INVALID JSON - {e}")
            all_ok = False
    else:
        messages.append("")
        if source_tree_mode:
            messages.append("hooks.json: not required for source tree validation")
        else:
            messages.append("hooks.json: MISSING")
            all_ok = False

    agents_path = _manifest_merged_file(codex_home, "AGENTS.md", manifest_override) or repo_root / "AGENTS.md"
    if agents_path.exists():
        content = agents_path.read_text(encoding="utf-8")
        if "codex-redteam-optin-mode:start" in content:
            messages.append("AGENTS.md: managed block present")
        else:
            messages.append("AGENTS.md: WARNING - no managed block found")
    else:
        if source_tree_mode:
            messages.append("AGENTS.md: not required for source tree validation")
        else:
            messages.append("AGENTS.md: MISSING")
            all_ok = False

    config_path = repo_root / "config.toml"
    if config_path.exists():
        try:
            tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
            messages.append("config.toml: valid")
        except (OSError, tomllib.TOMLDecodeError) as e:
            messages.append(f"config.toml: INVALID TOML - {e}")
            all_ok = False
    else:
        messages.append("config.toml: MISSING")
        all_ok = False

    skills_dir = _resolve_skills_dir(repo_root, source_tree_mode, manifest_override)
    if skills_dir is not None:
        messages.append("")
        messages.append(f"Installed skill cards: {skills_dir}")
        runtime_skills_dir = _resolve_runtime_skills_dir(codex_root, source_tree_mode)
        if runtime_skills_dir is not None:
            messages.append(f"Runtime skill cards: {runtime_skills_dir}")
            if runtime_skills_dir.resolve(strict=False) != skills_dir.resolve(strict=False):
                messages.append(
                    "  WARN runtime is not using the installed skill root; "
                    "reinstall with --enable-custom-skill-dirs to prioritize it"
                )
        for skill_id in REQUIRED_SKILL_IDS:
            skill_md = skills_dir / skill_id / "SKILL.md"
            if skill_md.exists():
                messages.append(f"  OK  {skill_id}/SKILL.md")
                ok, msg = check_skill_metadata(skill_md, skill_id)
                messages.append(msg)
                if not ok:
                    all_ok = False
            else:
                messages.append(f"  MISS {skill_id}/SKILL.md")
                all_ok = False

        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            skill_id = skill_md.parent.name
            ok, msg = check_skill_metadata(skill_md, skill_id)
            if not ok:
                messages.append(msg)
                all_ok = False

        legacy_cards = (
            list(skills_dir.glob("*/skill_card.yaml"))
            + list(skills_dir.glob("*/skill_card.yml"))
            + list(skills_dir.glob("*/skill_card.json"))
        )
        legacy_refs = [p for p in skills_dir.glob("*/references") if p.is_dir()]
        if legacy_cards or legacy_refs:
            messages.append("  FAIL legacy skill_card.* or references/ residue found")
            for residue in [*legacy_cards, *legacy_refs][:10]:
                try:
                    rel = residue.relative_to(repo_root)
                except ValueError:
                    rel = residue
                messages.append(f"       {rel}")
            all_ok = False
        else:
            messages.append("  OK  no legacy skill_card.* or references/ residue")
    elif not source_tree_mode:
        messages.append("agents/skills: MISSING")
        all_ok = False

    return all_ok, messages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate codex-redteam-optin-mode installation"
    )
    parser.add_argument(
        "--codex-home",
        required=False,
        help="Path to the codex home directory",
    )
    parser.add_argument(
        "--manifest",
        required=False,
        help="Candidate install manifest used during pre-commit validation",
    )
    args = parser.parse_args()

    codex_home = Path(args.codex_home) if args.codex_home else Path.home() / ".codex"
    if not codex_home.exists():
        print(f"ERROR: codex home directory does not exist: {codex_home}")
        sys.exit(1)

    manifest_override = Path(args.manifest) if args.manifest else None
    all_ok, messages = validate_install(codex_home, manifest_override)
    for msg in messages:
        print(msg)

    if all_ok:
        print("\nValidation PASSED.")
        sys.exit(0)
    else:
        print("\nValidation FAILED - some required files are missing.")
        sys.exit(1)

if __name__ == "__main__":
    main()

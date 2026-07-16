#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-install validation script for codex-redteam-optin-mode.

Verifies that all required files were deployed correctly and the install
is functional.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import List, Tuple


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")


REQUIRED_CODEX_FILES = [
    "redteam-mode/launcher.py",
    "redteam-mode/codex-redteam.cmd",
    "redteam-mode/codex-redteam",
    "hooks/session-start-context.py",
    "hooks/hook-security-context-hook.py",
    "hooks/stop-refusal-hook.py",
    "hooks/redteam_state.py",
    "hooks/core/emitter.py",
    "hooks/core/phase_detector.py",
    "hooks/core/semantic_phase.py",
    "hooks/core/loop_engine.py",
    "hooks/core/supplemental_prompts.py",
    "hooks/core/model_prompt_profiles.py",
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
    "prompts/Jailbreak.default.md",
    "prompts/Jailbreak.gpt-5.4.md",
    "prompts/Jailbreak.gpt-5.5.md",
    "prompts/Jailbreak.gpt-5.6.md",
]

REQUIRED_ROOT_FILES = [
    "config.toml",
]

SYSTEM_PROFILE_START = "<!-- codex-redteam-system-profile:start -->"
SYSTEM_PROFILE_END = "<!-- codex-redteam-system-profile:end -->"
MODEL_CATALOG_START = "<!-- codex-redteam-model-profiles:start -->"
MODEL_CATALOG_END = "<!-- codex-redteam-model-profiles:end -->"

OPTIONAL_CODEX_FILES = [
    "prompts/Reverse.md",
]

REQUIRED_SKILL_IDS = [
    "redteam-recon-intake",
    "redteam-cve-lookup",
    "redteam-cve-validation",
    "redteam-jailbreak-detail-pack",
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


def _load_manifest_data(repo_root: Path, manifest_override: Path | None) -> dict:
    manifest = manifest_override or repo_root / "redteam-install-manifest.json"
    if not manifest.is_file():
        return {}
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def check_system_prompt(repo_root: Path, codex_root: Path, manifest_override: Path | None) -> Tuple[bool, str]:
    config_path = repo_root / "config.toml"
    system_path = repo_root / "redteam-mode" / "system-instructions.md"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return False, f"system prompt: config unreadable - {exc}"
    reference = config.get("model_instructions_file")
    if not isinstance(reference, str) or not reference.strip():
        return False, "system prompt: model_instructions_file missing"
    configured_path = Path(reference).expanduser()
    if not configured_path.is_absolute():
        configured_path = config_path.parent / configured_path
    if configured_path.resolve(strict=False) != system_path.resolve(strict=False):
        return False, f"system prompt: config points to {configured_path.resolve(strict=False)}"
    try:
        content = system_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return False, f"system prompt: generated file unreadable - {exc}"
    pattern = re.escape(SYSTEM_PROFILE_START) + r"\s*(\{.*?\})\s*" + re.escape(SYSTEM_PROFILE_END)
    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        return False, "system prompt: profile marker missing"
    try:
        metadata = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return False, f"system prompt: invalid profile marker - {exc}"
    if not isinstance(metadata, dict) or metadata.get("layer") != "system":
        return False, "system prompt: profile marker is not system-layer"
    filename = metadata.get("profile_file") if isinstance(metadata, dict) else None
    if not isinstance(filename, str) or Path(filename).name != filename:
        return False, "system prompt: invalid profile filename"
    profile_path = codex_root / "prompts" / filename
    try:
        profile_content = profile_path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        return False, f"system prompt: profile unreadable - {exc}"
    if not profile_content or profile_content not in content:
        return False, f"system prompt: full profile content missing for {filename}"
    catalog = metadata.get("profile_catalog")
    if not isinstance(catalog, list) or not catalog:
        return False, "system prompt: model profile catalog metadata missing"
    for entry in catalog:
        catalog_filename = entry.get("profile_file") if isinstance(entry, dict) else None
        if not isinstance(catalog_filename, str) or Path(catalog_filename).name != catalog_filename:
            return False, "system prompt: invalid catalog profile filename"
        try:
            catalog_content = (codex_root / "prompts" / catalog_filename).read_text(encoding="utf-8-sig").strip()
        except OSError as exc:
            return False, f"system prompt: catalog profile unreadable - {exc}"
        if not catalog_content or catalog_content not in content:
            return False, f"system prompt: catalog profile content missing for {catalog_filename}"
    required_sections = (
        "# Codex red-team base instructions",
        "# Automatic model system profile router",
        MODEL_CATALOG_START,
        MODEL_CATALOG_END,
    )
    if not all(section in content for section in required_sections):
        return False, "system prompt: required composed sections missing"
    manifest_system = _load_manifest_data(repo_root, manifest_override).get("system_prompt")
    if isinstance(manifest_system, dict):
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if manifest_system.get("combined_sha256") != digest:
            return False, "system prompt: combined SHA256 mismatch"
        if manifest_system.get("profile_file") != filename or manifest_system.get("layer") != "system":
            return False, "system prompt: manifest metadata mismatch"
    return True, f"system prompt: valid ({metadata.get('profile')} -> {filename}, layer=system)"


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
    required_files = REQUIRED_CODEX_FILES
    if source_tree_mode:
        installed_launchers = {
            "redteam-mode/launcher.py",
            "redteam-mode/codex-redteam.cmd",
            "redteam-mode/codex-redteam",
        }
        required_files = [
            "launcher.py",
            *[rel for rel in REQUIRED_CODEX_FILES if rel not in installed_launchers],
        ]
    for rel in required_files:
        ok, msg = check_file(codex_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False
    root_files = ["instruction.ctf.md", *REQUIRED_ROOT_FILES] if source_tree_mode else REQUIRED_ROOT_FILES
    for rel in root_files:
        ok, msg = check_file(repo_root, rel)
        messages.append(msg)
        if not ok:
            all_ok = False

    if not source_tree_mode:
        ok, msg = check_system_prompt(repo_root, codex_root, manifest_override)
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
    configure_stdio()
    main()

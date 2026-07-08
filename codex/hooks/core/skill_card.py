"""Skill declaration card -- scope-not-instruct pattern.

A SkillCard defines WHAT domain the AI is operating in and WHAT evidence is
required to exit, without prescribing HOW to accomplish the goal. This keeps
the AI autonomous within bounded constraints.

Runtime source: SKILL.md (markdown with optional YAML frontmatter).
Parsing precedence: ## section headings > frontmatter fields.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass
class ExitGate:
    """Exit conditions for a skill domain."""

    required_artifacts: list[str] = field(default_factory=list)
    min_attempts_for_negative: int = 3


@dataclass
class SkillCard:
    """Lightweight skill declaration card parsed from SKILL.md."""

    skill_id: str
    display_name: str
    scope_summary: str
    forbidden_actions: list[str] = field(default_factory=list)
    pivot_hints: list[str] = field(default_factory=list)
    exit_gate: ExitGate = field(default_factory=ExitGate)

    def check_exit_gate(self, artifacts: list, loop_iteration: int) -> tuple[bool, str]:
        """Check whether exit conditions are met."""

        def _get_type(a: Any) -> str:
            if isinstance(a, dict):
                return a.get("type", "")
            return getattr(a, "type", "")

        def _is_verifiable(a: Any) -> bool:
            if isinstance(a, dict):
                return bool(a.get("verifiable", False))
            return bool(getattr(a, "verifiable", False))

        artifact_types = set()
        for a in artifacts:
            if _is_verifiable(a):
                t = _get_type(a)
                if t:
                    artifact_types.add(t)

        if not self.exit_gate.required_artifacts:
            return False, "exit_gate_not_declared"

        missing = [t for t in self.exit_gate.required_artifacts if t not in artifact_types]

        if not missing:
            return True, "all_required_artifacts_present"

        # Negative results are evidence too, but they should not silently close a
        # skill domain. Let the loop report the soft gate reason and keep the
        # current stage unless a caller explicitly records a negative artifact.
        if loop_iteration >= self.exit_gate.min_attempts_for_negative and not artifact_types:
            return False, "negative_evidence_required:" + ",".join(missing)

        return False, "missing_artifacts:" + ",".join(missing)


def _extract_sections(text: str) -> dict[str, str]:
    """Split markdown into {section_title_lower: section_body} dict."""
    positions = []
    for m in _SECTION_RE.finditer(text):
        positions.append((m.start(), m.end(), m.group(1).strip().lower()))
    sections: dict[str, str] = {}
    for i, (start, end, title) in enumerate(positions):
        body_start = end
        if i + 1 < len(positions):
            body_end = positions[i + 1][0]
        else:
            body_end = len(text)
        sections[title] = text[body_start:body_end].strip()
    return sections


def _extract_frontmatter(text: str) -> dict[str, str]:
    """Extract simple key: value pairs from YAML frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            result[key.strip()] = val
    return result


def _extract_title(text: str) -> str:
    """Extract the # top-level title from markdown."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""


def _parse_bullet_list(section_body: str) -> list[str]:
    """Parse markdown bullet list items from a section body."""
    items: list[str] = []
    for line in section_body.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _parse_exit_evidence(section_body: str) -> ExitGate:
    """Parse Exit Evidence section into an ExitGate.

    Uses a state machine: only bullet items under a 'Required artifacts:' header
    (or at the top level before any sub-header) are treated as required_artifacts.
    Sub-sections like 'Positive exit requires:', 'Negative exit requires:', etc.
    are descriptive and ignored.
    """
    required: list[str] = []
    min_attempts = 3
    # Start in required mode — bullets before any sub-header are required artifacts
    in_required_block = True

    for line in section_body.splitlines():
        line = line.strip()

        if not line:
            continue

        # Detect min_attempts anywhere (standalone line or bullet)
        if line.lower().startswith("min") and "attempt" in line.lower() and ":" in line:
            try:
                min_attempts = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            continue

        # Non-bullet lines ending with colon/Chinese colon are sub-section headers
        if not line.startswith("- ") and (line.endswith(":") or line.endswith("：")):
            lower = line.lower()
            in_required_block = (
                "required artifact" in lower
                or lower.startswith("required:")
                or lower.startswith("required artifact")
            )
            continue

        # Only parse bullets when in the required artifacts block
        if line.startswith("- ") and in_required_block:
            item = line[2:].strip()
            if item.lower().startswith("required:"):
                raw = item.split(":", 1)[1].strip()
                for p in raw.split(","):
                    p = p.strip()
                    if p:
                        required.append(p)
            elif item.lower().startswith("min_attempts:"):
                try:
                    min_attempts = int(item.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif item.lower().startswith("optional:"):
                pass
            else:
                required.append(item)

    return ExitGate(required_artifacts=required, min_attempts_for_negative=min_attempts)


def _parse_skill_md(text: str, skill_id: str) -> SkillCard:
    """Parse a SKILL.md file into a SkillCard.

    Handles two formats:
    1. New standard: ## Domain / ## Boundaries / ## Pivot Hints / ## Exit Evidence
    2. Legacy: frontmatter name/description + free sections
    """
    frontmatter = _extract_frontmatter(text)
    sections = _extract_sections(text)
    title = _extract_title(text)

    display_name = title or frontmatter.get("name", "") or skill_id

    scope_summary = sections.get("domain", "")
    if not scope_summary:
        scope_summary = frontmatter.get("description", "")

    forbidden_actions: list[str] = []
    if "boundaries" in sections:
        forbidden_actions = _parse_bullet_list(sections["boundaries"])

    pivot_hints: list[str] = []
    if "pivot hints" in sections:
        pivot_hints = _parse_bullet_list(sections["pivot hints"])

    exit_gate = ExitGate()
    if "exit evidence" in sections:
        exit_gate = _parse_exit_evidence(sections["exit evidence"])

    return SkillCard(
        skill_id=skill_id,
        display_name=display_name,
        scope_summary=scope_summary,
        forbidden_actions=forbidden_actions,
        pivot_hints=pivot_hints,
        exit_gate=exit_gate,
    )


# ---------------------------------------------------------------------------
# Path resolution + public loader
# ---------------------------------------------------------------------------

def resolve_skills_dir(codex_dir: Path) -> Path:
    """Resolve skills directory using 3-location fallback chain.

    Priority:
    1. $AGENTS_HOME/skills (env override)
    2. ~/.agents/skills (user-level)
    3. <repo_root>/agents/skills (repo-level)
    """
    agents_home = os.environ.get("AGENTS_HOME")
    if agents_home:
        env_skills = Path(agents_home) / "skills"
        if env_skills.is_dir():
            return env_skills

    user_skills = Path.home() / ".agents" / "skills"
    if user_skills.is_dir():
        return user_skills

    repo_skills = codex_dir.parent / "agents" / "skills"
    return repo_skills


def load_skill_card(skills_dir: Path, skill_id: str) -> "SkillCard | None":
    """Load a SkillCard from skills_dir/skill_id/SKILL.md.

    Returns None if skill_id is empty or SKILL.md is missing.
    On parse failure, returns a fallback card marked [skill-card:fallback].
    """
    if not skill_id:
        return None

    skill_md = skills_dir / skill_id / "SKILL.md"

    if not skill_md.is_file():
        logger.debug("No SKILL.md found at %s", skill_md)
        return None

    try:
        text = skill_md.read_text(encoding="utf-8")
        card = _parse_skill_md(text, skill_id)
        logger.info("Loaded skill card: %s (%s)", card.skill_id, card.display_name)
        return card
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse %s: %s -- returning fallback", skill_md, exc)
        return SkillCard(
            skill_id=skill_id,
            display_name=skill_id,
            scope_summary="[skill-card:fallback] Parse error: " + str(exc),
        )

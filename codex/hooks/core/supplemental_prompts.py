from __future__ import annotations

from pathlib import Path


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return ""


def _prompts_dir(codex_home: Path) -> Path:
    return codex_home / "prompts"


def build_prompt_chain_notice(codex_home: Path) -> str:
    """Return a minimal notice about active supplemental prompts, or empty string if none."""
    prompts_dir = _prompts_dir(codex_home)
    if not prompts_dir.exists():
        return ""

    active = [
        name
        for name, filename in (
            ("Reverse", "Reverse.md"),
        )
        if (prompts_dir / filename).exists()
    ]
    if not active:
        return ""

    joined = ",".join(active)
    return (
        f"[prompt-chain] instruction.ctf.md is highest priority. "
        f"Supplemental prompts/{joined} are active only as lower-priority phase hints."
    )


def build_prompt_overlay(codex_home: Path, phase: str = "") -> str:
    """Build a minimal phase-specific overlay. Only injects relevant supplements.

    Returns empty string when no phase-specific overlay is needed.
    """
    prompts_dir = _prompts_dir(codex_home)
    if not prompts_dir.exists():
        return ""

    lines: list[str] = []

    # Reverse.md — only for reverse phase
    if phase == "reverse":
        reverse_text = _read_text(prompts_dir / "Reverse.md")
        if reverse_text:
            lines.append("[overlay:Reverse|supplemental-phase]")
            lines.append(
                "Prioritize execution chain recovery, imports/strings/config extraction, "
                "and evidence-preserving analysis. Keep original and derived artifacts separate. "
                "Prove one path before expanding scope."
            )

    return "\n".join(lines)

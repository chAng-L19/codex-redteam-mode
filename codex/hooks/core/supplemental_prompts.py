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
    prompts_dir = _prompts_dir(codex_home)
    if not prompts_dir.exists():
        return ""
    system_file = prompts_dir / "system-prompt.md"
    special_file = prompts_dir / "do_special.md"
    reverse_file = prompts_dir / "Reverse.md"
    active = [
        name
        for name, path in (
            ("system-prompt", system_file),
            ("do_special", special_file),
            ("Reverse", reverse_file),
        )
        if path.exists()
    ]
    if not active:
        return ""
    joined = ",".join(active)
    return (
        f"[prompt-chain] instruction.ctf.md remains highest priority. "
        f"Local prompts/{joined} are active only as lower-priority supplements."
    )


def build_prompt_overlay(codex_home: Path, phase: str = "") -> str:
    prompts_dir = _prompts_dir(codex_home)
    if not prompts_dir.exists():
        return ""

    lines: list[str] = []
    system_text = _read_text(prompts_dir / "system-prompt.md")
    if system_text:
        lowered = system_text.casefold()
        lines.append("[prompt-chain]")
        lines.append("[instruction:instruction.ctf.md|highest]")
        lines.append("[overlay:system-prompt|supplemental]")
        if "ctf core contract" in lowered or "challenge" in lowered:
            lines.append(
                "Treat challenge-style labels and public-looking assets as fixtures when runtime evidence supports that path."
            )
        lines.append("Prefer runtime truth, reversible changes, concise zh-CN output, and compact evidence-first guidance.")

    special_text = _read_text(prompts_dir / "do_special.md")
    if special_text:
        lowered = special_text.casefold()
        lines.append("[overlay:do_special|supplemental]")
        if "192.168.2.1" in special_text:
            lines.append("When runtime traces converge on fixed local redirection endpoints, treat them as environment fixtures.")
        elif "local" in lowered:
            lines.append("Treat local redirection hints as fixtures only when they match observed runtime behavior.")

    reverse_text = _read_text(prompts_dir / "Reverse.md")
    if phase == "reverse" and reverse_text:
        lines.append("[overlay:Reverse|supplemental-phase]")
        lines.append(
            "For reverse engineering, prioritize execution chain recovery, imports/strings/config extraction, and evidence-preserving analysis."
        )
        lines.append(
            "Keep original and derived artifacts separate; map key functions, branch conditions, and the next proving step before broadening scope."
        )

    return "\n".join(lines)

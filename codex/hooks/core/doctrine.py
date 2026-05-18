from __future__ import annotations

from redteam_state import RedTeamState


def build_route_envelope(state: RedTeamState) -> str:
    selected = state.selected_path or state.leaf_skill or state.router or state.phase
    lines = [
        "[security:redteam]",
        f"[mode:{state.mode}]",
        f"[phase:{state.phase}]",
    ]
    if state.subphase:
        lines.append(f"[subphase:{state.subphase}]")
    if state.method:
        lines.append(f"[method:{state.method}]")
    if state.router:
        lines.append(f"[router:{state.router}]")
    if state.skill_pack:
        lines.append(f"[pack:{state.skill_pack}]")
    if state.leaf_skill:
        lines.append(f"[leaf:{state.leaf_skill}]")
    lines.append(f"[evidence:{state.evidence_level}]")
    lines.append(f"[opsec:{state.opsec_level}]")
    lines.append(f"[path:{selected}]")

    if state.mode == "redteam-full":
        lines.append("[workflow:structured-orchestration]")
        lines.append("[review:required]")
        lines.append("Use gates before delivery. Prefer the selected detailed pack, keep one selected path, attach evidence refs, and review before expansion.")
    else:
        review_flag = "required" if state.review_required else "optional"
        lines.append(f"[review:{review_flag}]")
        lines.append("Prefer the selected detailed pack, prove one path before expansion, distinguish facts from assumptions, and end with one concrete next step.")
    return "\n".join(lines)

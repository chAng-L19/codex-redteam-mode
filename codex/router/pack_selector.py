from __future__ import annotations
from .mappings import PHASE_DEFAULT_PACK, ROUTER_PACK_MAP
PHASE_FIRST_PACKS = {"ad","postex","reverse","code-audit","payload","evasion","cloud","container","network","crypto","mobile"}
def select_skill_pack(phase: str, router: str) -> str:
    if phase in PHASE_FIRST_PACKS:
        return PHASE_DEFAULT_PACK.get(phase, "red-team-command-doctrine")
    if router in ROUTER_PACK_MAP:
        return ROUTER_PACK_MAP[router]
    return PHASE_DEFAULT_PACK.get(phase, "red-team-command-doctrine")

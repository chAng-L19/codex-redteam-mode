from .doctrine import build_route_envelope
from .emitter import emit_hook_json
from .phase_detector import detect_phase, detect_phase_rule_based
from .prompt_parser import (
    decode_stdin,
    extract_prompt,
    extract_session_id,
    parse_mode_command,
    parse_opsec_command,
)
from .state_manager import load_runtime_state, reset_runtime_state, save_runtime_state
from .supplemental_prompts import build_prompt_chain_notice, build_prompt_overlay

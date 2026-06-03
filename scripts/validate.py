from __future__ import annotations
import argparse, importlib.util, io, json, os, runpy, sys
from pathlib import Path
class FakeIn:
    def __init__(self, b: bytes) -> None: self.buffer = io.BytesIO(b)
def assert_exists(path: Path) -> None:
    if not path.exists(): raise SystemExit(f"missing: {path}")
def run_hook(path: Path, payload: dict) -> str:
    old_stdin, old_stdout = sys.stdin, sys.stdout
    old_env = os.environ.copy()
    os.environ.setdefault("CODEX_REDTEAM_AUTO_PATCH", "0")
    buf = io.StringIO(); sys.stdout = buf; sys.stdin = FakeIn(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    try: runpy.run_path(str(path), run_name="__main__")
    finally: sys.stdin, sys.stdout = old_stdin, old_stdout; os.environ.clear(); os.environ.update(old_env)
    return buf.getvalue().strip()
def hook_context_len(output: str) -> int:
    if not output: return 0
    raw = json.loads(output)
    return len(raw["hookSpecificOutput"]["additionalContext"])
def status_line(name: str, ok: bool) -> str: return f"- {name}: {'ok' if ok else 'fail'}"
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--codex-home", default=str(Path.home()/".codex")); args = parser.parse_args(); codex_home = Path(args.codex_home)
    files=[codex_home/"redteam-install-manifest.json",codex_home/"instruction.ctf.md",codex_home/"prompts"/"system-prompt.md",codex_home/"prompts"/"do_special.md",codex_home/"prompts"/"Reverse.md",codex_home/"AGENTS.md",codex_home/"hooks.json",codex_home/"hooks"/"session-start-context.py",codex_home/"hooks"/"hook-security-context-hook.py",codex_home/"hooks"/"redteam_state.py",codex_home/"hooks"/"core"/"__init__.py",codex_home/"router"/"__init__.py",codex_home/"orchestrator"/"__init__.py"]
    for f in files: assert_exists(f)
    hooks_dir = codex_home/"hooks"
    for insert_path in (hooks_dir, codex_home):
        if str(insert_path) not in sys.path: sys.path.insert(0, str(insert_path))
    for idx, hook in enumerate([codex_home/"hooks"/"session-start-context.py", codex_home/"hooks"/"hook-security-context-hook.py", codex_home/"hooks"/"redteam_state.py"], start=1):
        name=f"validate_mod_{idx}"; spec=importlib.util.spec_from_file_location(name, hook); mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[name]=mod; spec.loader.exec_module(mod)
    session_hook=codex_home/"hooks"/"session-start-context.py"; prompt_hook=codex_home/"hooks"/"hook-security-context-hook.py"
    enable=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"进入红队模式"})
    reverse=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"分析这个 malware loader 样本并恢复执行链"})
    reverse_sem=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"这个程序会释放资源并拉起子进程，帮我梳理流程"})
    audit=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"审计这个 controller 和 middleware，从入口追到危险 sink"})
    audit_sem=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"帮我从入口一路追到危险函数，看看权限边界哪里失守"})
    postex_sem=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"已经拿到 shell，下一步应该如何做主机分诊和横向准备？"})
    cloud_route=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"Analyze AWS IAM role assumption and metadata credential abuse paths"})
    container_route=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"Assess kubernetes hostPath and privileged pod breakout risk"})
    network_route=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"Check HTTP/2 request smuggling and websocket protocol issues from this traffic"})
    crypto_route=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"Review this RSA and hash challenge for practical attack paths"})
    mobile_route=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"Analyze this Android APK with SSL pinning and Frida bypass considerations"})
    full_web=run_hook(prompt_hook, {"session_id":"validate-full","prompt":"进入红队模式"}); full_web=run_hook(prompt_hook, {"session_id":"validate-full","prompt":"/redteam full"}); full_web=run_hook(prompt_hook, {"session_id":"validate-full","prompt":"Review Burp JWT login traffic and verify token boundary reuse risks"})
    session_ctx=run_hook(session_hook, {"session_id":"validate-session"})
    ordinary=run_hook(prompt_hook, {"session_id":"validate-session-2","prompt":"Write a normal React page"})
    disable=run_hook(prompt_hook, {"session_id":"validate-main","prompt":"退出红队模式"})
    if str(codex_home) not in sys.path: sys.path.insert(0, str(codex_home))
    import orchestrator as orch
    recon=orch.ReconArtifact(scope="lab", hosts=["10.0.0.5"], ports=["80/tcp"], services=["http"], evidence_refs=["scan.json"], confidence=0.9)
    strategy=orch.StrategyArtifact(candidate_paths=[orch.StrategyPath(name="web-path", rationale="http present")], chosen_path="web-path", evidence_refs=["scan.json"])
    review=orch.ReviewArtifact(status="pass", next_action="deliver")
    manifest_file=codex_home/"redteam-install-manifest.json"; manifest_data=json.loads(manifest_file.read_text(encoding="utf-8")); manifest_ok=manifest_data.get("name")=="codex-redteam-optin-mode" and any(str(path).endswith("instruction.ctf.md") for path in manifest_data.get("managed_paths", []))
    checks=[("files",True),("install manifest",manifest_ok),("prompt chain session notice","instruction.ctf.md is highest priority" in session_ctx),("enable","enabled" in enable),("reverse phase","phase:reverse" in reverse),("reverse prompt overlay","[overlay:Reverse|supplemental-phase]" in reverse),("reverse semantic fallback","phase:reverse" in reverse_sem),("code-audit phase","phase:code-audit" in audit),("code-audit semantic fallback","phase:code-audit" in audit_sem),("postex semantic fallback","phase:postex" in postex_sem),("cloud routing","phase:cloud" in cloud_route and "pack:redteam-cloud-detail-pack" in cloud_route),("container routing","phase:container" in container_route and "pack:redteam-container-detail-pack" in container_route),("network routing","phase:network" in network_route and "pack:redteam-network-detail-pack" in network_route),("crypto routing","phase:crypto" in crypto_route and "pack:redteam-crypto-detail-pack" in crypto_route),("mobile routing","phase:mobile" in mobile_route and "pack:redteam-mobile-detail-pack" in mobile_route),("method/router/pack/leaf routing",all(token in full_web for token in ("router:", "pack:", "leaf:"))),("prompt overlays active","instruction.ctf.md is highest priority" in session_ctx and "[overlay:Reverse|supplemental-phase]" in reverse),("redteam-full distinction","[mode:redteam-full]" in full_web and "[workflow:structured-orchestration]" in full_web and "[review:required]" in full_web),("session start context size",hook_context_len(session_ctx)<=420),("ordinary prompt stays empty", ordinary==""),("recon gate",orch.recon_gate(recon).ok),("strategy gate",orch.strategy_gate(strategy).ok),("review gate",orch.review_gate(review).ok),("disable","disabled" in disable)]
    report=["# Validation Report","",*[status_line(n,o) for n,o in checks]]; print("\n".join(report))
    if not all(ok for _,ok in checks): raise SystemExit(1)
if __name__ == "__main__": main()

from __future__ import annotations
import io, json, runpy, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; HOOK=ROOT/'codex'/'hooks'/'hook-security-context-hook.py'; SESSION=ROOT/'codex'/'hooks'/'session-start-context.py'
class FakeIn:
    def __init__(self,b): self.buffer=io.BytesIO(b)
def run_script(path, payload=None):
    old_stdin, old_stdout=sys.stdin, sys.stdout; buf=io.StringIO(); sys.stdout=buf; data=b'' if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8'); sys.stdin=FakeIn(data)
    try: runpy.run_path(str(path), run_name='__main__')
    finally: sys.stdin, sys.stdout = old_stdin, old_stdout
    return buf.getvalue().strip()
class HookTests(unittest.TestCase):
    def test_session_and_clean_mode(self):
        out=run_script(SESSION, {'session_id':'size-check'}); self.assertIn('instruction.ctf.md remains highest priority', out); self.assertEqual('', run_script(HOOK, {'session_id':'size-check','prompt':'Write a normal React page'}))
    def test_full_mode_auth_pack(self):
        run_script(SESSION, {'session_id':'full'}); run_script(HOOK, {'session_id':'full','prompt':'/redteam full'}); full=run_script(HOOK, {'session_id':'full','prompt':'Review Burp JWT login traffic and verify token boundary reuse risks'}); self.assertIn('[mode:redteam-full]', full); self.assertIn('[pack:redteam-auth-detail-pack]', full)
    def test_expanded_domain_packs(self):
        run_script(SESSION, {'session_id':'exp'}); run_script(HOOK, {'session_id':'exp','prompt':'/redteam on'}); self.assertIn('pack:redteam-cloud-detail-pack', run_script(HOOK, {'session_id':'exp','prompt':'Analyze AWS IAM role assumption and metadata credential abuse paths'})); self.assertIn('pack:redteam-mobile-detail-pack', run_script(HOOK, {'session_id':'exp','prompt':'Analyze this Android APK with SSL pinning and Frida bypass considerations'}))
if __name__=='__main__': unittest.main()

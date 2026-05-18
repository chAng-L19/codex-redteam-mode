from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; INSTALL=ROOT/'scripts'/'install.py'
class InstallTests(unittest.TestCase):
    def test_install_preserves_existing_agents_and_hooks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); codex_home=base/'codex-home'; agents_home=base/'agents-home'; codex_home.mkdir(parents=True); agents_home.mkdir(parents=True)
            (codex_home/'AGENTS.md').write_text('# User AGENTS\n\n- keep my custom rules\n', encoding='utf-8')
            (codex_home/'hooks.json').write_text(json.dumps({'hooks':{'UserPromptSubmit':[{'hooks':[{'type':'command','command':'python custom_hook.py','statusMessage':'User custom hook','timeout':10}]}]}}, ensure_ascii=False, indent=2), encoding='utf-8')
            cmd=[sys.executable, str(INSTALL), '--codex-home', str(codex_home), '--agents-home', str(agents_home)]
            subprocess.run(cmd, check=True); subprocess.run(cmd, check=True)
            merged=(codex_home/'AGENTS.md').read_text(encoding='utf-8'); self.assertIn('keep my custom rules', merged); self.assertEqual(1, merged.count('codex-redteam-optin-mode:start'))
            hooks=json.loads((codex_home/'hooks.json').read_text(encoding='utf-8')); statuses=[hook.get('statusMessage') for entries in hooks.get('hooks',{}).values() for entry in entries for hook in entry.get('hooks',[])]; self.assertIn('User custom hook', statuses); self.assertEqual(1, statuses.count('Loading session mode context')); self.assertEqual(1, statuses.count('Checking mode-gated offensive routing'))
if __name__=='__main__': unittest.main()

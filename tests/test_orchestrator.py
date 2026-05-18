import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'codex'))
import orchestrator as orch
class OrchTests(unittest.TestCase):
    def test_gates(self):
        recon=orch.ReconArtifact(scope='lab', hosts=['1.1.1.1'], ports=['80/tcp'], services=['http'], evidence_refs=['scan'], confidence=0.9)
        self.assertTrue(orch.recon_gate(recon).ok)
if __name__=='__main__': unittest.main()

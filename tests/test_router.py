from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'codex'))
from router import select_leaf_skill, select_method, select_router, select_skill_pack, select_subphase
class RouterTests(unittest.TestCase):
    def test_auth_pack(self):
        p='Review Burp JWT login traffic and verify token boundary reuse risks'
        self.assertEqual(select_router(p,'web'),'auth-sec'); self.assertEqual(select_skill_pack('web','auth-sec'),'redteam-auth-detail-pack'); self.assertEqual(select_leaf_skill(p,'web','auth-sec'),'jwt-oauth-token-attacks')
    def test_reverse_pack(self):
        p='The sample unpacks resources and launches a child process; help me recover the loader chain'
        self.assertEqual(select_router(p,'reverse'),'malware-loader-analysis'); self.assertEqual(select_subphase(p,'reverse'),'loader'); self.assertEqual(select_skill_pack('reverse','malware-loader-analysis'),'redteam-reverse-detail-pack')
    def test_expanded(self):
        self.assertEqual(select_skill_pack('cloud','cloud-iam-abuse'),'redteam-cloud-detail-pack')
        self.assertEqual(select_skill_pack('container','container-escape-techniques'),'redteam-container-detail-pack')
        self.assertEqual(select_skill_pack('network','websocket-security'),'redteam-network-detail-pack')
        self.assertEqual(select_skill_pack('crypto','hash-attack-techniques'),'redteam-crypto-detail-pack')
        self.assertEqual(select_skill_pack('mobile','mobile-ssl-pinning-bypass'),'redteam-mobile-detail-pack')
if __name__=='__main__': unittest.main()

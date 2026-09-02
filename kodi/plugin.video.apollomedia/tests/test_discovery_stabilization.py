import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
M=(ROOT/"main.py").read_text()
A=(ROOT/"resources/lib/ams.py").read_text()
D=(REPO/"apollo_media_server/app/api/discovery.py").read_text()
P=(REPO/"apollo_media_server/app/api/progress.py").read_text()
class TestDiscoveryStabilization(unittest.TestCase):
    def test_pagination(self):
        self.assertIn('"More Results"',M)
        self.assertIn('params={"page":max(1,int(page or 1))}',A)
    def test_unaired_still_playable(self):
        self.assertIn("def _episode_air_label",M)
        body=M.split("def discovery_season(p):",1)[1].split("\ndef ",1)[0]
        self.assertIn("playable_media(",body)
    def test_runtime_guard_contract(self):
        self.assertIn('"expected_duration_seconds"',D)
        self.assertIn("expected_duration",M)
    def test_progress_cutoffs(self):
        self.assertIn("if position < 10:",P)
        self.assertIn("remaining <= 20",P)
if __name__=="__main__": unittest.main()

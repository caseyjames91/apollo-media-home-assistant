from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'main.py').read_text()
class EpisodeContractTests(unittest.TestCase):
    def test_first_aired(self): self.assertIn('tag.setFirstAired(air_date[:10])', MAIN)
    def test_expected_duration(self):
        self.assertIn('row.get("expected_duration_seconds")', MAIN)
        self.assertIn('float(row.get("runtime") or 0)*60', MAIN)
if __name__ == "__main__": unittest.main()

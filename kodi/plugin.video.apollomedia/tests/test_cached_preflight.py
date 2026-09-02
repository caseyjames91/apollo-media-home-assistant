import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=(ROOT/"resources/lib/sources.py").read_text()
M=(ROOT/"main.py").read_text()
V=(ROOT/"service.py").read_text()
class TestCachedPreflight(unittest.TestCase):
    def test_cache_api(self):
        self.assertIn("/v1/api/torrents/checkcached",S)
        self.assertIn("list_files",S)
        self.assertIn("cached_only=True",S)
    def test_archive_guard(self):
        self.assertIn("archive_only",S)
        self.assertIn("has_video and not archive_only",S)
    def test_uncached_fallback(self):
        self.assertIn("No cached playable streams were found",M)
        self.assertIn("Search uncached sources?",M)
    def test_duration_guard(self):
        self.assertIn("position < 10.0",V)
        self.assertIn("ApolloExpectedDuration",V)
        self.assertIn("ignoring implausible duration",V)
if __name__=="__main__": unittest.main()

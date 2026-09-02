import ast
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
M=(ROOT/"main.py").read_text()
S=(ROOT/"service.py").read_text()
A=(ROOT/"resources/lib/ams.py").read_text()
SRC=(ROOT/"resources/lib/sources.py").read_text()

class Repair031(unittest.TestCase):
    def test_air_label_presentation(self):
        self.assertIn("item.setLabel(display_label)",M)
        self.assertIn("Airing on ",M)
    def test_complete_playback_contract(self):
        for x in ("ApolloSeriesTitle","ApolloTmdbId","ApolloExpectedDuration"):
            self.assertIn(x,M)
        self.assertIn("report_duration=self.expected_duration",S)
        self.assertIn('"series_title": str(series_title or "") or None',A)
    def test_provider_asserted_cache_is_accepted(self):
        # 0.10.32 supersedes the 0.10.31 hash requirement.
        self.assertIn("elif provider_asserted:",SRC)
        self.assertNotIn("elif provider_asserted and key:",SRC)
        self.assertIn("stream.cached=True",SRC)
    def test_parse(self):
        for p in (ROOT/"main.py",ROOT/"service.py",ROOT/"resources/lib/ams.py",ROOT/"resources/lib/sources.py"):
            ast.parse(p.read_text())
if __name__=="__main__":
    unittest.main()

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()


class CanonicalDetailContract099Tests(unittest.TestCase):
    def test_library_show_uses_canonical_discovery_renderer(self):
        start = MAIN.index('def add_ams_library_show(row, presentation_context="library"):')
        end = MAIN.index("\n\n\ndef library():", start)
        block = MAIN[start:end]
        self.assertIn("add_discovery_series(", block)
        self.assertIn("local=True", block)
        self.assertIn("native_local=True", block)
        self.assertNotIn("xbmcplugin.addDirectoryItem", block)

    def test_canonical_show_route_carries_library_capability(self):
        start = MAIN.index("def add_discovery_series(")
        end = MAIN.index("\n\n\ndef add_discovery_season(", start)
        block = MAIN[start:end]
        self.assertIn("in_library=bool(local or native_local)", block)
        self.assertIn('action="discovery_seasons"', block)
        self.assertIn('media_type="show"', block)

    def test_library_and_discovery_share_one_show_route_builder(self):
        library_start = MAIN.index('def add_ams_library_show(row, presentation_context="library"):')
        library_end = MAIN.index("\n\n\ndef library():", library_start)
        library_block = MAIN[library_start:library_end]
        self.assertNotIn('action="discovery_seasons"', library_block)
        self.assertIn("add_discovery_series(", library_block)


if __name__ == "__main__":
    unittest.main()

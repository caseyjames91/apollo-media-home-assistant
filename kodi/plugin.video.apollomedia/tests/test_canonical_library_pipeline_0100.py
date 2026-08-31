from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()


class CanonicalLibraryPipeline0100Tests(unittest.TestCase):
    def test_kodi_root_exposes_library_routes(self):
        start = MAIN.index("def home():")
        end = MAIN.index("\ndef finish_action():", start)
        block = MAIN[start:end]
        self.assertIn('add_folder("Library Movies", "library")', block)
        self.assertIn('add_folder("Library Shows", "series_library")', block)

    def test_remote_library_uses_ams_canonical_renderer(self):
        start = MAIN.index("def remote_media_list(")
        block = MAIN[start:]
        self.assertIn('list_type == "library_shows"', block)
        self.assertIn('remote_ams_library("series"', block)

        start = MAIN.index('def add_ams_library_show(')
        end = MAIN.index("\n\n\ndef library():", start)
        renderer = MAIN[start:end]
        self.assertIn("add_discovery_series(", renderer)
        self.assertNotIn("xbmcplugin.addDirectoryItem", renderer)

    def test_legacy_library_route_contract_is_gone(self):
        self.assertNotIn("jellyfin_item_id", MAIN)
        self.assertNotIn('action="seasons"', MAIN)
        self.assertNotIn("series_id=", MAIN)

    def test_show_navigation_has_one_canonical_action(self):
        self.assertIn('action="discovery_seasons"', MAIN)


if __name__ == "__main__":
    unittest.main()

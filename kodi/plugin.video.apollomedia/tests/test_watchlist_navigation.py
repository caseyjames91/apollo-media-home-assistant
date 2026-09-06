import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKodiWatchlistContract(unittest.TestCase):
    def test_ams_client_owns_watchlist_requests(self):
        ams = (ROOT / "resources" / "lib" / "ams.py").read_text()
        self.assertIn("def watchlist(addon):", ams)
        self.assertIn('f"profiles/{pid}/watchlist"', ams)
        self.assertIn("def watchlist_contains(addon, media_id):", ams)
        self.assertIn("def set_watchlist(addon, media_id, watchlisted):", ams)
        self.assertEqual(ams.count("def watchlist_contains(addon, media_id):"), 1)
        self.assertEqual(ams.count("def set_watchlist(addon, media_id, watchlisted):"), 1)
        self.assertIn('method="PUT"', ams)
        self.assertIn('method="DELETE"', ams)

    def test_home_exposes_watchlist_navigation(self):
        main = (ROOT / "main.py").read_text()
        home = main.split("def home():", 1)[1].split("\ndef ", 1)[0]
        self.assertIn('folder("Watchlist", url("watchlist"))', home)

    def test_watchlist_reuses_existing_canonical_rendering(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def watchlist():", 1)[1].split(
            "\ndef _canonical_detail_target", 1
        )[0]
        self.assertIn("rows = ams.watchlist(ADDON)", block)
        self.assertIn('playable_media(row, "movie")', block)
        self.assertIn("_canonical_detail_target(row)", block)
        self.assertNotIn("play_remote(", block)
        self.assertNotIn("find_streams(", block)

    def test_only_title_media_get_watchlist_context(self):
        main = (ROOT / "main.py").read_text()
        helper = main.split("def _watchlist_context(", 1)[1].split(
            "\ndef _play_context", 1
        )[0]
        self.assertIn('normalized not in ("movie", "show")', helper)
        self.assertIn("Apollo: Add to Watchlist", helper)
        self.assertIn("Apollo: Remove from Watchlist", helper)

    def test_routes_are_dispatched(self):
        main = (ROOT / "main.py").read_text()
        self.assertIn('elif action == "watchlist":', main)
        self.assertIn("        watchlist()", main)
        self.assertIn('elif action == "set_watchlist":', main)
        self.assertIn("        set_watchlist(p)", main)

    def test_release_version_stays_01058_until_release(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('version="0.10.58"', addon)


if __name__ == "__main__":
    unittest.main()

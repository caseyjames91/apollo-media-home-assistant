import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
MAIN = (ROOT / "main.py").read_text()
AMS = (ROOT / "resources/lib/ams.py").read_text()
SERVER = (REPO / "apollo_media_server/app/api/discovery.py").read_text()

class RemoteShowNavigationTests(unittest.TestCase):
    def test_placeholder_is_gone(self):
        self.assertNotIn("Remote playback coming in provider stage", MAIN)
        self.assertNotIn('"remote_pending"', MAIN)

    def test_library_uses_canonical_show_route(self):
        self.assertIn('url("discovery_show", tmdb=tmdb', MAIN)

    def test_show_and_season_use_ams(self):
        self.assertIn("ams.discovery_show(ADDON, tmdb)", MAIN)
        self.assertIn("ams.discovery_season(ADDON, tmdb, season_number)", MAIN)
        self.assertIn('action == "discovery_season"', MAIN)

    def test_episode_reuses_playable_media(self):
        body = MAIN.split("def discovery_season(p):", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("playable_media(", body)

    def test_ams_contract(self):
        self.assertIn("def discovery_show(addon, tmdb_id):", AMS)
        self.assertIn("def discovery_season(addon, tmdb_id, season):", AMS)
        self.assertIn('@router.get("/show/{tmdb_id}")', SERVER)
        self.assertIn('@router.get("/show/{tmdb_id}/season/{season_number}")', SERVER)

if __name__ == "__main__":
    unittest.main()

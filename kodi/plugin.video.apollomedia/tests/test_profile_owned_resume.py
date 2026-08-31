import unittest
from pathlib import Path
import sys

ADDON_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from resources.lib import ams


class FakeAddon:
    def __init__(self, values=None):
        self.values = values or {}

    def getSettingString(self, key):
        return self.values.get(key, "")


class ProfileOwnedResumeTests(unittest.TestCase):
    def setUp(self):
        self.addon = FakeAddon({
            "ams_url": "http://ams.test:8099",
            "ams_profile_id": "profile-1",
        })

    def test_resume_reads_configured_profile_continue_watching(self):
        original = ams._request
        calls = []
        try:
            def fake_request(addon, path, method="GET", payload=None, timeout=6):
                calls.append((path, method, payload))
                return [{
                    "imdb_id": "tt123",
                    "season": None,
                    "episode": None,
                    "position_seconds": 1800,
                    "duration_seconds": 7200,
                }]
            ams._request = fake_request
            self.assertEqual(
                ams.resume_progress(self.addon, "tt123", "movie", 0, 0),
                (1800.0, 7200.0),
            )
            self.assertEqual(calls[0][0], "profiles/profile-1/continue-watching")
        finally:
            ams._request = original

    def test_successful_profile_lookup_without_match_is_authoritative_zero(self):
        original = ams._request
        try:
            ams._request = lambda *args, **kwargs: []
            self.assertEqual(
                ams.resume_progress(self.addon, "tt123", "movie", 0, 0),
                (0.0, 0.0),
            )
        finally:
            ams._request = original

    def test_episode_resume_matches_profile_and_episode_identity(self):
        original = ams._request
        try:
            ams._request = lambda *args, **kwargs: [
                {"imdb_id": "ttshow", "season": 1, "episode": 1, "position_seconds": 300, "duration_seconds": 3600},
                {"imdb_id": "ttshow", "season": 1, "episode": 2, "position_seconds": 900, "duration_seconds": 3600},
            ]
            self.assertEqual(
                ams.resume_progress(self.addon, "ttshow", "episode", 1, 2),
                (900.0, 3600.0),
            )
        finally:
            ams._request = original

    def test_start_over_reset_writes_zero_to_same_profile(self):
        original = ams._request
        captured = {}
        try:
            def fake_request(addon, path, method="GET", payload=None, timeout=6):
                captured.update(path=path, method=method, payload=payload)
                return {"status": "ok"}
            ams._request = fake_request
            self.assertTrue(ams.reset_progress(self.addon, "tt123", "movie", 0, 0, "Movie"))
            self.assertEqual(captured["path"], "progress")
            self.assertEqual(captured["method"], "PUT")
            self.assertEqual(captured["payload"]["profile_id"], "profile-1")
            self.assertEqual(captured["payload"]["position_seconds"], 0.0)
        finally:
            ams._request = original

    def test_main_resume_path_prefers_ams_and_has_no_jellyfin_reset(self):
        source = ADDON_ROOT.joinpath("main.py").read_text(encoding="utf-8")
        self.assertIn("ams.resume_progress(ADDON, imdb_id, media_type, season, episode)", source)
        self.assertIn("ams.reset_progress(ADDON, imdb_id, media_type, season, episode, title)", source)
        self.assertNotIn("Could not reset Jellyfin resume", source)
        resume_start = source.index("def canonical_local_resume")
        local_get = source.index("progress.get(imdb_id, season, episode)", resume_start)
        ams_get = source.index("ams.resume_progress", resume_start)
        self.assertLess(ams_get, local_get)


if __name__ == "__main__":
    unittest.main()

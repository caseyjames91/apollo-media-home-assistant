import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resources.lib.playback_validation import duration_valid


class PlaybackValidationTests(unittest.TestCase):
    def test_waits_until_kodi_exposes_duration(self):
        self.assertIsNone(duration_valid(0, 1320))

    def test_rejects_error_clip_against_episode_runtime(self):
        self.assertFalse(duration_valid(30, 1320))

    def test_accepts_normal_episode_duration(self):
        self.assertTrue(duration_valid(1280, 1320))

    def test_matches_ams_lower_ratio_boundary(self):
        self.assertTrue(duration_valid(660, 1320))
        self.assertFalse(duration_valid(659, 1320))

    def test_matches_ams_upper_ratio_boundary(self):
        self.assertTrue(duration_valid(2310, 1320))
        self.assertFalse(duration_valid(2311, 1320))

    def test_short_duration_fallback_without_runtime(self):
        self.assertFalse(duration_valid(30, 0))

    def test_sixty_seconds_is_allowed_by_fallback(self):
        self.assertTrue(duration_valid(60, 0))


if __name__ == "__main__":
    unittest.main()

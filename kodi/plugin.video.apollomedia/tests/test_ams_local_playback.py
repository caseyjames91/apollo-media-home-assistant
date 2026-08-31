import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
AMS = (ROOT / "resources" / "lib" / "ams.py").read_text(encoding="utf-8")
SETTINGS = (ROOT / "resources" / "settings.xml").read_text(encoding="utf-8")


class AmsLocalPlaybackTests(unittest.TestCase):
    def test_device_key_setting_exists(self):
        self.assertIn('id="ams_device_key"', SETTINGS)

    def test_ams_identity_resolution_is_strict(self):
        self.assertIn('def find_media(', AMS)
        self.assertIn('row.get("imdb_id")', AMS)
        self.assertNotIn('title_match', AMS)

    def test_unified_resolver_uses_ams_playback_resolution(self):
        self.assertIn('ams.resolve_playback_for_identity(', MAIN)
        self.assertIn('mode == "local"', MAIN)
        self.assertIn('mode == "remote"', MAIN)
        self.assertIn('"ams_local"', MAIN)

    def test_normal_local_route_uses_unified_resolver(self):
        start = MAIN.index('def resolved_playback_item(')
        end = MAIN.index('def play_resolved(', start)
        body = MAIN[start:end]
        self.assertIn('source == "ams"', body)
        self.assertIn('ams.resolve_playback_for_identity(', body)
        self.assertNotIn('source == "jellyfin"', body)


if __name__ == "__main__":
    unittest.main()

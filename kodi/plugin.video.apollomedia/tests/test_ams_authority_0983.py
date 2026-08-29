import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "service.py").read_text(encoding="utf-8")
AMS = (ROOT / "resources/lib/ams.py").read_text(encoding="utf-8")
SETTINGS = (ROOT / "resources/settings.xml").read_text(encoding="utf-8")


class AmsAuthority0983Tests(unittest.TestCase):
    def test_kodi_gui_and_headless_consume_ams_first(self):
        self.assertIn("def ams_continue_watching_rows", MAIN)
        self.assertIn("rows = ams_continue_watching_rows(sync_jellyfin=True)", MAIN)
        self.assertIn("add_ams_continue_item(row, card_playback=False)", MAIN)
        self.assertIn("add_ams_continue_item(row, card_playback=True)", MAIN)

    def test_kodi_reports_progress_to_ams(self):
        self.assertIn('ams_reporter(', SERVICE)
        self.assertIn('"progress/import"', AMS)

    def test_card_artwork_is_blob_backed(self):
        self.assertIn("async amsArtworkBlobUrl", CARD)
        self.assertIn("URL.createObjectURL(blob)", CARD)
        self.assertIn("hydrateAmsArtwork", CARD)

    def test_ams_refresh_does_not_run_shared_ha_refresh(self):
        self.assertIn("With AMS enabled, refresh is intentionally card-local", CARD)
        self.assertIn("Do not touch\n        // the legacy shared HA Continue Watching sensor", CARD)

    def test_kodi_has_ams_connection_settings(self):
        self.assertIn('id="ams_url"', SETTINGS)
        self.assertIn('http://homeassistant.local:8099', SETTINGS)


if __name__ == "__main__":
    unittest.main()

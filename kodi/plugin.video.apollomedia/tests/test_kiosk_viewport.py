import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class KioskViewportTests(unittest.TestCase):
    def test_detects_kiosk_url_parameter(self):
        self.assertIn('new URLSearchParams(window.location.search || "").has("kiosk")', CARD)

    def test_app_marks_kiosk_state(self):
        self.assertIn('data-kiosk="${kioskMode ? "true" : "false"}"', CARD)

    def test_kiosk_uses_full_dynamic_viewport(self):
        self.assertIn('.app[data-kiosk="true"] {', CARD)
        self.assertIn('--apollo-view-offset: 0px;', CARD)
        self.assertIn('height: calc(100dvh - var(--apollo-view-offset));', CARD)

    def test_non_kiosk_keeps_ha_header_offset(self):
        self.assertIn('--apollo-view-offset: 56px;', CARD)

    def test_release_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()

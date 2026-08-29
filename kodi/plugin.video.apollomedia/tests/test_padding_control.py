import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class PaddingControlTests(unittest.TestCase):
    def test_change_padding_control_exists(self):
        self.assertIn('class="padding-size-open"', CARD)
        self.assertIn('Change Padding', CARD)
        self.assertIn('class="padding-popup-slider"', CARD)

    def test_spacing_range(self):
        self.assertIn('min="6"', CARD)
        self.assertIn('max="28"', CARD)

    def test_spacing_is_global_and_persistent(self):
        self.assertIn('localStorage.setItem("apollo-media.card-spacing", String(safeSize))', CARD)

    def test_spacing_variable_drives_rails_and_grid(self):
        self.assertIn('--apollo-card-gap:', CARD)
        self.assertIn('gap: var(--apollo-card-gap);', CARD)
        self.assertIn('column-gap: var(--apollo-card-gap);', CARD)

    def test_default_and_reset_are_14px(self):
        self.assertIn('savedCardSpacing ?? 14', CARD)
        self.assertIn('this.setCardSpacing(14, true);', CARD)

    def test_release_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class TextSizePopupTests(unittest.TestCase):
    def test_button_and_popup(self):
        self.assertIn('class="text-size-open"', CARD)
        self.assertIn('Change Text Size', CARD)
        self.assertIn('class="text-size-popup-slider"', CARD)

    def test_range(self):
        self.assertIn('min="80"', CARD)
        self.assertIn('max="130"', CARD)

    def test_per_context_persistence(self):
        self.assertIn('apollo-media.text-scale.${context}', CARD)
        self.assertIn('this.textScales[context] = this.textScale;', CARD)

    def test_css_scale_variable(self):
        self.assertIn('var(--apollo-text-scale, 1)', CARD)
        self.assertIn('--apollo-text-scale:', CARD)

    def test_release_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class PosterSizePopupTests(unittest.TestCase):
    def test_display_options_uses_button_not_inline_slider(self):
        self.assertIn('class="poster-size-open"', CARD)
        self.assertIn('Change Poster Size', CARD)
        self.assertNotIn('class="poster-size-slider"', CARD)

    def test_popup_contains_slider(self):
        self.assertIn('class="poster-size-overlay"', CARD)
        self.assertIn('class="poster-size-popup-slider"', CARD)
        self.assertIn('min="90"', CARD)
        self.assertIn('max="150"', CARD)

    def test_popup_uses_global_poster_size(self):
        self.assertIn('this._posterSizePopupContext = context;', CARD)
        self.assertIn('const size = this.posterSize || 118;', CARD)
        self.assertIn('localStorage.setItem("apollo-media.poster-size", String(safeSize))', CARD)

    def test_live_slider_uses_existing_size_setter(self):
        self.assertIn('this.setPosterSize(Number(event.target.value), false);', CARD)
        self.assertIn('this.setPosterSize(Number(event.target.value), true);', CARD)

if __name__ == "__main__":
    unittest.main()

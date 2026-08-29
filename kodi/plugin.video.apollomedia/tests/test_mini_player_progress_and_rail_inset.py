import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class MiniPlayerProgressAndRailInsetTests(unittest.TestCase):
    def test_mini_player_progress_markup_exists(self):
        self.assertIn('class="now-playing-mini-progress"', CARD)
        self.assertIn('data-now-playing-mini-progress', CARD)

    def test_mini_progress_uses_live_position_and_duration(self):
        self.assertIn('(position / duration) * 100', CARD)
        self.assertIn('miniProgress.style.width = `${progressPercent}%`;', CARD)

    def test_mini_progress_is_bottom_edge_bar(self):
        self.assertIn('.now-playing-mini-progress {', CARD)
        self.assertIn('bottom: 0;', CARD)
        self.assertIn('height: 3px;', CARD)

    def test_tiny_rail_scroll_offsets_are_normalized(self):
        self.assertIn('normalizeRailScrollLeft(value)', CARD)
        self.assertIn('return numeric <= 24 ? 0 : numeric;', CARD)

    def test_scroll_state_uses_normalizer_on_capture_and_restore(self):
        self.assertIn('this.normalizeRailScrollLeft(row.querySelector(".horizontal-row")?.scrollLeft || 0)', CARD)
        self.assertIn('rail.scrollLeft = this.normalizeRailScrollLeft(scrollLeft);', CARD)

    def test_rail_css_preserves_leading_inset(self):
        self.assertIn('padding: 0 17px;', CARD)
        self.assertIn('scroll-padding-inline: 17px;', CARD)
        self.assertIn('overflow-anchor: none;', CARD)

    def test_release_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()

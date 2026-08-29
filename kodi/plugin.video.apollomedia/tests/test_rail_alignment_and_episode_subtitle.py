import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class RailAlignmentAndEpisodeSubtitleTests(unittest.TestCase):
    def test_episode_subtitle_regex_accepts_space_between_season_episode(self):
        self.assertIn(r'subtitle.replace(/^S\d+\s*E\d+\s*[•·]\s*/i, "").trim()', CARD)

    def test_rail_is_explicitly_top_aligned(self):
        self.assertIn(".horizontal-row {\n          display: flex;\n          align-items: flex-start;", CARD)
        self.assertIn("align-self: flex-start;", CARD)

    def test_two_line_title_reservation_is_preserved(self):
        self.assertIn(".rail-poster-item .poster-title", CARD)
        self.assertIn("height: 2.4em;", CARD)
        self.assertIn("min-height: 2.4em;", CARD)

    def test_card_version_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()

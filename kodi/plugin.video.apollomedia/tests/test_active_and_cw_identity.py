import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT/"main.py").read_text(encoding="utf-8")
CARD = (ROOT.parent/"apollo-media-card.js").read_text(encoding="utf-8")

class ActiveAndCWIdentityTests(unittest.TestCase):
    def test_active_context_not_title_gated(self):
        start = CARD.index("  activeApolloContext(player) {")
        end = CARD.index("\n  ", start + len("  activeApolloContext(player) {"))
        # broad source assertion is enough; title equality gate must be gone
        self.assertNotIn("kodiTitle !== activeTitle", CARD)
        self.assertIn("playerEpisode", CARD)



    def test_discovery_episodes_uses_canonical_imdb(self):
        start = MAIN.index("def discovery_episodes(")
        end = MAIN.index("\ndef ", start + 5)
        block = MAIN[start:end]
        self.assertIn("series_details(imdb_id)", block)
        self.assertNotIn("jellyfin", block.lower())


if __name__ == "__main__":
    unittest.main()

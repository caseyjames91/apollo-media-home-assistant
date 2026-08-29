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

    def test_local_identity_lookup_exists(self):
        self.assertIn("def local_item_for_identity(", MAIN)
        self.assertIn("jf.series_index()", MAIN)
        self.assertIn("jf.episodes(series_id)", MAIN)

    def test_apollo_cw_recovers_local_capabilities(self):
        start = MAIN.index("def add_external_progress(")
        end = MAIN.index("\ndef ", start + 5)
        block = MAIN[start:end]
        self.assertIn("local_item_for_identity(", block)
        self.assertIn("jellyfin_item_id=local_item_id", block)
        self.assertIn("in_library=bool(local_item_id)", block)
        self.assertIn("remote_auto_target=remote_auto_target", block)
        self.assertIn("remote_choose_target=remote_choose_target", block)
        self.assertIn("card_play_target=card_play_target", block)
        self.assertIn("resume_item_id=local_item_id", block)

    def test_show_episodes_backfills_series_imdb(self):
        start = MAIN.index("def show_episodes(")
        end = MAIN.index("\ndef ", start + 5)
        block = MAIN[start:end]
        self.assertIn("if not imdb_id and series_id:", block)
        self.assertIn('series_ids.get("Imdb")', block)

if __name__ == "__main__":
    unittest.main()

import unittest
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class NowPlayingSourceClassifierTests(unittest.TestCase):
    def test_expected_local_overrides_original_remote_path(self):
        self.assertIn('if (expected === "local") return false;', CARD)
        self.assertIn('if (expected === "remote") return true;', CARD)

    def test_active_context_precedes_original_card_path(self):
        start = CARD.index("  isApolloRemotePlaybackActive(player) {")
        end_match = re.search(r"\n  [A-Za-z0-9_]+\([^)]*\) \{", CARD[start + 1:])
        self.assertIsNotNone(end_match)
        end = start + 1 + end_match.start()
        method = CARD[start:end]
        self.assertIn("const active = this.activeApolloContext(player);", method)
        self.assertIn("if (active) return Boolean(active.remote);", method)

    def test_source_invalidation_forces_structural_rebuild(self):
        self.assertIn("this._nowPlayingIdentity = null;", CARD)

    def test_switch_completion_rebuilds_open_modal(self):
        self.assertGreaterEqual(CARD.count("if (this._nowPlayingOpen) this.rebuildNowPlayingModal(this._nowPlayingPlayer);"), 2)

if __name__ == "__main__":
    unittest.main()

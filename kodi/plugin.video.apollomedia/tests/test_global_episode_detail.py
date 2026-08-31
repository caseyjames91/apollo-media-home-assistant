import unittest
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class GlobalEpisodeDetailTests(unittest.TestCase):
    def test_card_route_model_has_safe_play_target(self):
        self.assertIn('"card_play_target": str(card_play_target or "")', MAIN)
        self.assertIn("playTarget: params.card_play_target || file.file || \"\"", CARD)
        self.assertIn("const localPath = String(item.playTarget || item.file || item.path || \"\");", CARD)

    def test_discovery_episode_routes_through_ams(self):
        start = MAIN.index("def add_discovery_episode(")
        end_match = re.search(r"\ndef [A-Za-z0-9_]+\(", MAIN[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(MAIN)
        block = MAIN[start:end]
        self.assertIn('action="play_resolved"', block)
        self.assertIn('source="ams"', block)
        self.assertNotIn('play_jellyfin', block)

    def test_discovery_local_episode_has_card_safe_target(self):
        start = MAIN.index("def add_discovery_episode(")
        end_match = re.search(r"\ndef [A-Za-z0-9_]+\(", MAIN[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(MAIN)
        block = MAIN[start:end]
        self.assertIn("card_play_target=plugin_url(", block)
        self.assertIn('action="play_resolved"', block)

if __name__ == "__main__":
    unittest.main()

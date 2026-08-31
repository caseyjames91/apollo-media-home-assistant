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

    def test_show_episodes_has_global_local_capabilities(self):
        start = MAIN.index("def show_episodes(")
        end_match = re.search(r"\ndef [A-Za-z0-9_]+\(", MAIN[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(MAIN)
        block = MAIN[start:end]
        self.assertIn("remote_auto_target=remote_auto_target", block)
        self.assertIn("remote_choose_target=remote_choose_target", block)
        self.assertIn("card_play_target=card_play_target", block)
        self.assertIn('in_library="1"', block)

    def test_kodi_native_episode_route_is_not_card_play_target(self):
        start = MAIN.index("def show_episodes(")
        end_match = re.search(r"\ndef [A-Za-z0-9_]+\(", MAIN[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(MAIN)
        block = MAIN[start:end]
        self.assertIn('action="play_jellyfin_native" if native_local else "play_jellyfin"', block)
        self.assertIn('action="play_resolved"', block)
        self.assertIn('source="ams"', block)
        self.assertIn('action="play_jellyfin_native" if native_local else "play_jellyfin"', block)

    def test_discovery_local_episode_has_card_safe_target(self):
        start = MAIN.index("def add_discovery_episode(")
        end_match = re.search(r"\ndef [A-Za-z0-9_]+\(", MAIN[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(MAIN)
        block = MAIN[start:end]
        self.assertIn("card_play_target=plugin_url(", block)
        self.assertIn('action="play_resolved"', block)

if __name__ == "__main__":
    unittest.main()

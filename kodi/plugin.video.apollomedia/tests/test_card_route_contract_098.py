import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CARD = (ROOT.parents[1] / "card" / "apollo-media-card.js").read_text(encoding="utf-8")

class CardRouteContract098Tests(unittest.TestCase):
    def test_library_movie_exports_local_and_remote_capabilities(self):
        body = MAIN[MAIN.index("def add_ams_library_movie("):MAIN.index("def _ams_local_series_rows(")]
        self.assertIn("in_library=True", body)
        self.assertIn("remote_card_targets(", body)
        self.assertIn("card_play_target=local_target", body)

    def test_local_show_capability_survives_navigation(self):
        seasons = MAIN[MAIN.index("def discovery_seasons("):MAIN.index("def discovery_episodes(")]
        episodes = MAIN[MAIN.index("def discovery_episodes("):MAIN.index("def continue_watching(")]
        self.assertIn("bool(native_local)", seasons)
        self.assertIn("bool(native_local)", episodes)
        add_episode = MAIN[MAIN.index("def add_discovery_episode("):MAIN.index("def home(")]
        self.assertIn('in_library="1" if local else "0"', add_episode)

    def test_card_prefers_plugin_route_season(self):
        self.assertIn('hasParamSeason = Object.prototype.hasOwnProperty.call(params, "season")', CARD)
        self.assertIn('rawSeason = hasParamSeason && Number.isFinite(paramSeason)', CARD)
        self.assertIn('season = hasParamSeason && Number.isFinite(paramSeason) ? paramSeason : itemSeason', CARD)

    def test_local_button_remains_capability_driven(self):
        self.assertIn('item.in_library && item.remoteAutoTarget', CARD)
        self.assertIn('data-title-play-local', CARD)

if __name__ == "__main__":
    unittest.main()

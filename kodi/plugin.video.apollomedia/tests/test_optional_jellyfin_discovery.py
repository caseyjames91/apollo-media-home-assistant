import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class ApolloDiscoveryTests(unittest.TestCase):
    def test_season_discovery_has_no_jellyfin_dependency(self):
        start = MAIN.index("def discovery_seasons(")
        end = MAIN.index("def discovery_episodes(", start)
        body = MAIN[start:end]

        self.assertIn("series_details(imdb_id)", body)
        self.assertIn("add_discovery_season(", body)
        self.assertNotIn("jellyfin", body.lower())
        self.assertNotIn("require_jellyfin", body)
        self.assertNotIn("jf.", body)

    def test_episode_discovery_has_no_jellyfin_dependency(self):
        start = MAIN.index("def discovery_episodes(")
        end = MAIN.index("def continue_watching(", start)
        body = MAIN[start:end]

        self.assertIn("series_details(imdb_id)", body)
        self.assertIn("add_discovery_episode(", body)
        self.assertNotIn("jellyfin", body.lower())
        self.assertNotIn("require_jellyfin", body)
        self.assertNotIn("jf.", body)


if __name__ == "__main__":
    unittest.main()

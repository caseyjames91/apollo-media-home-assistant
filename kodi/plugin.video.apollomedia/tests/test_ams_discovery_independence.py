import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).parents[1]
MAIN = ADDON_ROOT.joinpath("main.py").read_text(encoding="utf-8")


def function_body(name):
    start = MAIN.index(f"def {name}(")
    try:
        end = MAIN.index("\ndef ", start + 1)
    except ValueError:
        end = len(MAIN)
    return MAIN[start:end]


class AmsDiscoveryIndependenceTests(unittest.TestCase):
    def test_movie_search_does_not_require_jellyfin(self):
        body = function_body("search")
        self.assertIn("search_movies(query)", body)
        self.assertIn("add_discovery_movie(", body)
        self.assertNotIn("require_jellyfin()", body)
        self.assertNotIn("media_service().search_movies", body)

    def test_show_search_does_not_require_jellyfin(self):
        body = function_body("search_tv")
        self.assertIn("search_series(query)", body)
        self.assertIn("add_discovery_series(", body)
        self.assertNotIn("require_jellyfin()", body)
        self.assertNotIn("media_service().search_shows", body)

    def test_discovery_navigation_does_not_require_jellyfin(self):
        self.assertNotIn("require_jellyfin()", function_body("discovery_seasons"))
        self.assertNotIn("require_jellyfin()", function_body("discovery_episodes"))

    def test_movie_discovery_enters_ams_resolver(self):
        body = function_body("play_discovery")
        self.assertIn('play_resolved(', body)
        self.assertIn('"ams"', body)
        self.assertNotIn("find_movie(", body)

    def test_episode_discovery_enters_ams_resolver(self):
        body = function_body("add_discovery_episode")
        self.assertIn('source="ams"', body)

    def test_unified_resolver_has_identity_first_ams_branch(self):
        body = function_body("resolved_playback_item")
        self.assertIn('if source == "ams":', body)
        self.assertIn("ams.resolve_playback_for_identity(", body)
        self.assertIn('"ams_local"', body)
        self.assertIn("playback_path", body)


if __name__ == "__main__":
    unittest.main()

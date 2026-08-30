import re
import unittest
from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "main.py"
SOURCE = MAIN.read_text(encoding="utf-8")


def function_source(name):
    match = re.search(
        rf"^def {re.escape(name)}\(.*?(?=^def |\Z)",
        SOURCE,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError(f"Could not find function {name}")
    return match.group(0)


class OptionalJellyfinDiscoveryTests(unittest.TestCase):
    def test_season_discovery_does_not_fail_with_jellyfin(self):
        source = function_source("discovery_seasons")
        self.assertIn("series_details(imdb_id)", source)
        self.assertIn("if jf.ready:", source)
        self.assertIn("try:", source)
        self.assertIn("jf.find_series(imdb_id)", source)
        self.assertIn("Optional Jellyfin season enrichment failed", source)
        self.assertIn("for season_number in seasons:", source)

    def test_episode_discovery_does_not_fail_with_jellyfin(self):
        source = function_source("discovery_episodes")
        self.assertIn("series_details(imdb_id)", source)
        self.assertIn("if jf.ready:", source)
        self.assertIn("try:", source)
        self.assertIn("jf.find_series(imdb_id)", source)
        self.assertIn("Optional Jellyfin episode enrichment failed", source)
        self.assertIn("for episode in discovered:", source)


if __name__ == "__main__":
    unittest.main()

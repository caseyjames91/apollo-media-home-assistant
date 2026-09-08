import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestWatchedContextState(unittest.TestCase):
    def test_playable_media_passes_resolved_watched_state_to_context(self):
        source = (ROOT / "main.py").read_text()
        block = source.split("def playable_media(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("watched = False", block)
        self.assertIn("watched=watched", block)

    def test_play_context_exposes_only_inverse_watched_action(self):
        source = (ROOT / "main.py").read_text()
        block = source.split("def _play_context(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("watched=False", block)
        self.assertIn("if watched:", block)

        watched_branch = block.split("if watched:", 1)[1].split("else:", 1)[0]
        unwatched_branch = block.split("else:", 1)[1].split("if row.get", 1)[0]

        self.assertIn('"Apollo: Mark unwatched"', watched_branch)
        self.assertNotIn('"Apollo: Mark watched"', watched_branch)
        self.assertIn('"Apollo: Mark watched"', unwatched_branch)
        self.assertNotIn('"Apollo: Mark unwatched"', unwatched_branch)


if __name__ == "__main__":
    unittest.main()

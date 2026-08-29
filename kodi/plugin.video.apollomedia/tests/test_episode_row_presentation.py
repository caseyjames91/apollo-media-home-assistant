import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class EpisodeRowPresentationTests(unittest.TestCase):
    def test_episode_name_is_primary_cell_title(self):
        self.assertIn('(child.episode_title || child.title || "Untitled")', CARD)

    def test_episode_meta_is_compact_season_episode_code(self):
        self.assertIn('class="episode-inline-meta"', CARD)
        self.assertIn('`S${Number(child.season || expectedSeason || 0)} E${Number(child.episode || 0)}`', CARD)

    def test_episode_progress_is_not_drawn_on_thumbnail(self):
        self.assertIn('{ ...child, progress: undefined, resume_position: 0, resume_duration: 0 }', CARD)
        self.assertIn('class="episode-inline-progress"', CARD)

    def test_remote_source_badge_is_hidden(self):
        self.assertIn('const sourceLabel = !remoteApollo && activeApollo ? "LOCAL" : "";', CARD)
        self.assertNotIn('["REMOTE STREAM", activeApollo?.provider', CARD)

if __name__ == "__main__":
    unittest.main()

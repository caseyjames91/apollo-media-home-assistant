import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_matcher():
    source = (ROOT / "main.py").read_text()
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name == "_source_session_matches_item"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, str(ROOT / "main.py"), "exec"), namespace)
    return namespace["_source_session_matches_item"]

class TestContextSessionIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matches = staticmethod(load_matcher())

    def test_movie_session_matches_same_movie(self):
        self.assertTrue(self.matches(
            {"imdb_id": "tt123", "media_type": "movie", "season": 0, "episode": 0},
            {"imdb_id": "tt123"}, "movie",
        ))

    def test_movie_session_rejects_different_movie(self):
        self.assertFalse(self.matches(
            {"imdb_id": "tt999", "media_type": "movie", "season": 0, "episode": 0},
            {"imdb_id": "tt123"}, "movie",
        ))

    def test_episode_requires_same_season_and_episode(self):
        session = {"imdb_id": "tt123", "media_type": "series", "season": 1, "episode": 3}
        row = {"imdb_id": "tt123"}
        self.assertTrue(self.matches(session, row, "series", season=1, episode=3))
        self.assertFalse(self.matches(session, row, "series", season=1, episode=4))
        self.assertFalse(self.matches(session, row, "series", season=2, episode=3))

    def test_missing_session_or_identity_never_matches(self):
        self.assertFalse(self.matches(None, {"imdb_id": "tt123"}, "movie"))
        self.assertFalse(self.matches({"imdb_id": ""}, {"imdb_id": "tt123"}, "movie"))

    def test_play_context_gates_stream_tools_through_identity_match(self):
        source = (ROOT / "main.py").read_text()
        block = source.split("def _play_context(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("_source_session_matches_item(", block)
        self.assertNotIn("if source_session.load():", block)
        self.assertIn('"Apollo: Current Stream Info"', block)
        self.assertIn('"Apollo: Try Next Stream"', block)
        self.assertIn('"Apollo: Flag Current Stream"', block)

if __name__ == "__main__":
    unittest.main()

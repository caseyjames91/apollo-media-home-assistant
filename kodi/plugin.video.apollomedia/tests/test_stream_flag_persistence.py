import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "resources/lib/source_session.py"


class Stream:
    def __init__(self, title, url, description="", provider="torrentio"):
        self.title = title
        self.url = url
        self.description = description
        self.provider = provider


class StreamFlagPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        fake_xbmcvfs = types.SimpleNamespace(
            translatePath=lambda _value: self.tempdir.name,
        )
        self.previous = sys.modules.get("xbmcvfs")
        sys.modules["xbmcvfs"] = fake_xbmcvfs

        spec = importlib.util.spec_from_file_location("apollo_source_session_test", MODULE_PATH)
        self.session = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.session)

    def tearDown(self):
        if self.previous is None:
            sys.modules.pop("xbmcvfs", None)
        else:
            sys.modules["xbmcvfs"] = self.previous
        self.tempdir.cleanup()

    def save(self, streams):
        return self.session.save(
            streams,
            "tt1234567",
            "movie",
            0,
            0,
            "Test Movie",
        )

    def test_flag_survives_provider_url_refresh(self):
        original = [
            Stream("Movie.2026.1080p.WEB-DL-GROUP", "https://old/one"),
            Stream("Movie.2026.1080p.BluRay-OTHER", "https://old/two"),
        ]
        self.save(original)
        self.session.flag_index(0, "buffering")

        refreshed = [
            Stream("Movie.2026.1080p.WEB-DL-GROUP", "https://new/one"),
            Stream("Movie.2026.1080p.BluRay-OTHER", "https://new/two"),
        ]
        data = self.save(refreshed)

        self.assertEqual(data["index"], 1)
        self.assertTrue(self.session.is_flagged(0))
        self.assertFalse(self.session.is_flagged(1))
        self.assertEqual(self.session.current()["url"], "https://new/two")
        flag = self.session.flag_for_url("https://new/one")
        self.assertIsNotNone(flag)
        self.assertEqual(flag["reason"], "buffering")
        self.assertEqual(flag["url"], "https://new/one")
        self.assertTrue(flag["stream_key"])

    def test_all_flagged_streams_do_not_fall_back_to_index_zero(self):
        original = [
            Stream("Movie.Release.One", "https://old/one"),
            Stream("Movie.Release.Two", "https://old/two"),
        ]
        self.save(original)
        self.session.flag_index(0, "buffering")
        self.session.flag_index(1, "wrong_language")

        data = self.save([
            Stream("Movie.Release.One", "https://new/one"),
            Stream("Movie.Release.Two", "https://new/two"),
        ])

        self.assertEqual(data["index"], -1)
        self.assertIsNone(self.session.current())
        self.assertTrue(self.session.is_flagged(0))
        self.assertTrue(self.session.is_flagged(1))

    def test_legacy_url_only_flag_is_upgraded_when_same_release_returns(self):
        self.save([Stream("Movie.Release.One", "https://old/one")])
        data = self.session.load()
        data["flags"] = [{
            "reason": "buffering",
            "url": "https://old/one",
            "title": "Movie.Release.One",
            "created": 123.0,
        }]
        with open(self.session._path(), "w", encoding="utf-8") as handle:
            self.session.json.dump(data, handle)

        refreshed = self.save([Stream("Movie.Release.One", "https://new/one")])
        self.assertEqual(refreshed["index"], -1)
        self.assertEqual(refreshed["flags"][0]["url"], "https://new/one")
        self.assertTrue(refreshed["flags"][0]["stream_key"])


if __name__ == "__main__":
    unittest.main()

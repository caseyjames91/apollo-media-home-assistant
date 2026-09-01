import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_profile = tempfile.mkdtemp(prefix="apollo-source-session-")
xbmcvfs = types.ModuleType("xbmcvfs")
xbmcvfs.translatePath = lambda value: _profile
sys.modules.setdefault("xbmcvfs", xbmcvfs)

from resources.lib import source_session


def row(title, quality, key):
    return {
        "title": title,
        "url": f"https://example/{key}",
        "provider": "torrentio",
        "quality": quality,
        "stream_key": key,
        "release_aliases": [key],
    }


class SourceSessionAdvanceTests(unittest.TestCase):
    def setUp(self):
        self.path = source_session._path()
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def save(self, streams, index, flags=None):
        data = {
            "created": source_session.time.time(),
            "index": index,
            "imdb_id": "tt1",
            "media_type": "movie",
            "season": 0,
            "episode": 0,
            "title": "Test",
            "streams": streams,
            "flags": flags or [],
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_manual_1080_selection_stays_in_1080_tier(self):
        streams = [
            row("4K A", "4K / 2160p", "4ka"),
            row("4K B", "4K / 2160p", "4kb"),
            row("1080 A", "1080p", "1080a"),
            row("1080 B", "1080p", "1080b"),
            row("720 A", "720p", "720a"),
        ]
        self.save(streams, 2)
        data, stream = source_session.advance()
        self.assertEqual(data["index"], 3)
        self.assertEqual(stream["stream_key"], "1080b")

    def test_does_not_wrap_back_to_higher_ranked_4k(self):
        streams = [
            row("4K A", "4K / 2160p", "4ka"),
            row("1080 A", "1080p", "1080a"),
            row("1080 B", "1080p", "1080b"),
        ]
        self.save(streams, 2)
        data, stream = source_session.advance()
        self.assertIsNone(stream)
        self.assertEqual(data["index"], 2)

    def test_falls_to_next_lower_tier(self):
        streams = [
            row("1080 A", "1080p", "1080a"),
            row("720 A", "720p", "720a"),
            row("480 A", "SD / 480p", "480a"),
        ]
        self.save(streams, 0)
        data, stream = source_session.advance()
        self.assertEqual(data["index"], 1)
        self.assertEqual(stream["stream_key"], "720a")

    def test_permanent_flag_is_skipped(self):
        streams = [
            row("1080 A", "1080p", "1080a"),
            row("1080 B", "1080p", "1080b"),
            row("1080 C", "1080p", "1080c"),
        ]
        flag = {
            "stream_key": "1080b",
            "release_aliases": ["1080b"],
            "reason": "wrong_content",
        }
        self.save(streams, 0, [flag])
        data, stream = source_session.advance()
        self.assertEqual(data["index"], 2)
        self.assertEqual(stream["stream_key"], "1080c")

    def test_temporary_failure_does_not_create_flag(self):
        streams = [
            row("1080 A", "1080p", "1080a"),
            row("1080 B", "1080p", "1080b"),
            row("1080 C", "1080p", "1080c"),
        ]
        self.save(streams, 0)
        data, stream = source_session.advance(failed_keys={"1080b"})
        self.assertEqual(data["index"], 2)
        self.assertEqual(stream["stream_key"], "1080c")
        self.assertEqual(data.get("flags"), [])


if __name__ == "__main__":
    unittest.main()

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

http = types.ModuleType("resources.lib.http")
http.get_json = lambda *args, **kwargs: {}
sys.modules.setdefault("resources.lib.http", http)

from resources.lib.sources import Stream, dedupe_streams
from resources.lib.stream_identity import identity_aliases, release_key, same_release


class StreamIdentityTests(unittest.TestCase):
    def test_hash_is_primary_identity(self):
        row = Stream(
            "Movie.1080p.WEB-DL.mkv",
            "https://example/play?token=one",
            provider="torrentio",
            info_hash="ABCDEF1234",
        )
        self.assertEqual(release_key(row), "hash:abcdef1234")

    def test_rotating_url_does_not_change_filename_identity(self):
        first = Stream(
            "Movie.1080p.WEB-DL-GROUP.mkv",
            "https://example/play?token=one",
        )
        second = Stream(
            "Movie.1080p.WEB-DL-GROUP.mkv",
            "https://example/play?token=two",
        )
        self.assertTrue(same_release(first, second))

    def test_hash_provider_and_filename_only_provider_can_match(self):
        hashed = Stream(
            "Movie.1080p.WEB-DL-GROUP.mkv",
            "a",
            info_hash="0123456789abcdef",
        )
        filename_only = Stream(
            "Movie.1080p.WEB-DL-GROUP.mkv",
            "b",
        )
        self.assertTrue(same_release(hashed, filename_only))

    def test_legacy_bare_title_key_remains_alias(self):
        row = Stream("Movie.1080p.WEB-DL-GROUP.mkv", "a")
        self.assertIn("movie1080pwebdlgroupmkv", identity_aliases(row))

    def test_dedupe_uses_provider_priority_for_same_release(self):
        streams = [
            Stream(
                "Movie.1080p.WEB-DL-GROUP.mkv",
                "torrentio-url",
                provider="torrentio",
                info_hash="deadbeef",
            ),
            Stream(
                "Movie.1080p.WEB-DL-GROUP.mkv",
                "debridio-url",
                provider="debridio",
                info_hash="deadbeef",
            ),
        ]
        result = dedupe_streams(
            streams,
            {"provider_priority": "debridio,torrentio"},
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].provider, "debridio")

    def test_different_releases_remain_distinct(self):
        streams = [
            Stream("Movie.1080p.WEB-DL-A.mkv", "a", provider="torrentio"),
            Stream("Movie.1080p.WEB-DL-B.mkv", "b", provider="torrentio"),
        ]
        self.assertEqual(len(dedupe_streams(streams, {})), 2)


if __name__ == "__main__":
    unittest.main()

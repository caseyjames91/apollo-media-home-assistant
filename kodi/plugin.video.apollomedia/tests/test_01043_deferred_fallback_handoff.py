import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_profile = tempfile.mkdtemp(prefix="apollo-01043-")

xbmcvfs = types.ModuleType("xbmcvfs")
xbmcvfs.translatePath = lambda value: _profile
sys.modules.setdefault("xbmcvfs", xbmcvfs)

from resources.lib import source_session


def row(title, key):
    return {
        "title": title,
        "url": "https://example/" + key,
        "provider": "torrentio",
        "quality": "1080p",
        "stream_key": key,
        "release_aliases": [key],
    }


class DeferredFallbackHandoff043(unittest.TestCase):
    def setUp(self):
        try:
            os.unlink(source_session._path())
        except FileNotFoundError:
            pass

        data = {
            "created": source_session.time.time(),
            "index": 0,
            "imdb_id": "tt1",
            "media_type": "movie",
            "season": 0,
            "episode": 0,
            "title": "Test",
            "streams": [
                row("Bad", "bad"),
                row("Replacement", "good"),
            ],
            "flags": [],
            "attempts": {
                "state": "idle",
                "failed_keys": [],
            },
        }

        with open(
            source_session._path(),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(data, handle)

    def test_failure_becomes_pending_before_replacement_is_claimed(self):
        source_session.begin_attempt(0)
        source_session.start_attempt()

        data, stream = source_session.fail_attempt(
            "implausible_duration"
        )

        self.assertEqual(data["index"], 1)
        self.assertEqual(stream["stream_key"], "good")

        attempts = source_session.attempt_state()
        self.assertEqual(attempts["state"], "retry_pending")
        self.assertEqual(attempts["index"], 1)

        failed_at = float(attempts["failed_at"])

        # During teardown, replacement remains pending.
        self.assertIsNone(
            source_session.claim_pending_retry(
                settle_seconds=0.75,
                now=failed_at + 0.25,
            )
        )
        self.assertEqual(
            source_session.attempt_state()["state"],
            "retry_pending",
        )

        # Once teardown has settled, exactly one caller can promote it.
        index = source_session.claim_pending_retry(
            settle_seconds=0.75,
            now=failed_at + 1.0,
        )

        self.assertEqual(index, 1)

        attempts = source_session.attempt_state()
        self.assertEqual(attempts["state"], "requested")
        self.assertEqual(attempts["index"], 1)
        replacement = (source_session.load() or {})["streams"][1]
        self.assertEqual(
            attempts["stream_key"],
            source_session._stream_key(replacement),
        )
        self.assertIn("bad", attempts["failed_keys"])

        # The same retry cannot be claimed twice.
        self.assertIsNone(
            source_session.claim_pending_retry(
                settle_seconds=0.75,
                now=failed_at + 2.0,
            )
        )

    def test_failure_callback_does_not_start_replacement_playback(self):
        service = (ROOT / "service.py").read_text()

        start = service.index("def _retry_failed_attempt")
        end = service.index("class MonitorPlayer", start)
        block = service[start:end]

        self.assertNotIn("PlayMedia(", block)
        self.assertIn("retry pending index=", block)

    def test_service_loop_owns_replacement_launch(self):
        service = (ROOT / "service.py").read_text()

        self.assertIn(
            'attempts.get("state") == "retry_pending"',
            service,
        )
        self.assertIn(
            'not player.isPlayingVideo()',
            service,
        )
        self.assertIn(
            'source_session.claim_pending_retry()',
            service,
        )
        self.assertIn(
            'launching deferred retry index=',
            service,
        )
        self.assertIn(
            '_plugin_url("play_session_stream", index=retry_index)',
            service,
        )


if __name__ == "__main__":
    unittest.main()

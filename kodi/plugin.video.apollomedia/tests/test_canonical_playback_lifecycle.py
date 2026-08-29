import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

class CanonicalPlaybackLifecycleTests(unittest.TestCase):
    def test_unified_listitem_does_not_apply_kodi_startoffset(self):
        source = ROOT.joinpath("main.py").read_text(encoding="utf-8")
        start = source.index("def external_item(")
        end = source.index("\ndef current_stream_info", start)
        body = source[start:end]
        self.assertNotIn('setProperty("StartOffset"', body)
        self.assertIn("tag.setResumePoint(float(position), float(duration))", body)

    def test_monitor_is_single_absolute_start_authority(self):
        source = ROOT.joinpath("service.py").read_text(encoding="utf-8")
        self.assertIn("self.seekTime(requested)", source)
        self.assertIn("requested_start_position", source)

    def test_both_resolvers_create_playback_session(self):
        source = ROOT.joinpath("main.py").read_text(encoding="utf-8")
        resolver = source[source.index("def resolved_playback_item("):source.index("\ndef play_resolved(", source.index("def resolved_playback_item("))]
        self.assertIn('playback_session.save(\n            "jellyfin"', resolver)
        self.assertIn('playback_session.save(\n            "remote"', resolver)

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT.parent / "apollo-media-card.js"
HA = ROOT.parent / "ha" / "apollo_home_assistant_prototype.yaml"

class NativeResumeAndCardControlsTests(unittest.TestCase):
    def test_resolved_item_exposes_resume_point_without_startoffset(self):
        source = ROOT.joinpath("main.py").read_text(encoding="utf-8")
        start = source.index("def external_item(")
        end = source.index("\ndef current_stream_info", start)
        body = source[start:end]
        self.assertIn("tag.setResumePoint(float(position), float(duration))", body)
        self.assertNotIn('setProperty("StartOffset"', body)

    def test_initial_resume_is_not_post_avstart_seek(self):
        source = ROOT.joinpath("service.py").read_text(encoding="utf-8")
        self.assertIn('resume_mode == "live"', source)
        self.assertIn("self.seekTime(requested)", source)

    def test_native_remote_path_has_no_second_apollo_resume_dialog(self):
        source = ROOT.joinpath("main.py").read_text(encoding="utf-8")
        start = source.index("def play_external_resolved_prompt(")
        end = source.index("\ndef play_external(", start)
        body = source[start:end]
        self.assertNotIn("choose_resume_start(", body)
        self.assertIn('"native"', body)

    def test_card_playeropen_passes_explicit_resume_choice(self):
        source = HA.read_text(encoding="utf-8")
        self.assertIn('options:', source)
        self.assertIn('resume: "{{ resume | bool }}"', source)

    def test_card_scrub_uses_transient_position(self):
        source = CARD.read_text(encoding="utf-8")
        self.assertIn("_nowPlayingScrubPosition", source)
        self.assertIn("this._nowPlayingSeeking && Number.isFinite(scrubPosition)", source)

    def test_card_play_pause_is_state_explicit(self):
        source = CARD.read_text(encoding="utf-8")
        self.assertIn('state === "playing") return this.runNowPlayingControl("media_pause")', source)
        self.assertIn('state === "paused") return this.runNowPlayingControl("media_play")', source)
        self.assertNotIn('runNowPlayingControl("media_play_pause")', source)

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SESSION = (ROOT / "resources/lib/source_session.py").read_text(encoding="utf-8")
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")
HA = (ROOT.parent / "ha/apollo_home_assistant_prototype.yaml").read_text(encoding="utf-8")


class SourcePolicyAndQualityTests(unittest.TestCase):
    def test_card_remote_is_default_but_local_path_is_retained(self):
        self.assertIn('const useRemoteDefault = sourcePreference !== "local" && Boolean(remotePath);', CARD)
        self.assertIn('await this.playApolloItem(this.selectedTitle, resumable ? "resume" : null, "local")', CARD)

    def test_remote_to_local_native_handoff_exists(self):
        self.assertNotIn("def remote_play_jellyfin(", MAIN)
        self.assertIn('action=play_resolved', HA)
        self.assertIn('source=ams', HA)
        self.assertIn("apollo_switch_local:", HA)
        self.assertIn("data-now-playing-switch-local", CARD)
        block = HA.split("apollo_switch_local:", 1)[1].split("\n  apollo_play:", 1)[0]
        self.assertIn("&resume_mode=resume", block)
        self.assertNotIn("&resume_mode=live", block)

    def test_stream_session_owns_quality_classification(self):
        self.assertIn("def _technical_info(", SESSION)
        self.assertIn('"quality": quality', SESSION)
        self.assertIn('"video": " · ".join', SESSION)
        self.assertIn('"audio": audio or "Unknown audio"', SESSION)

    def test_stream_picker_uses_addon_quality_metadata(self):
        self.assertIn("apollo_quality=str(stream.get(\"quality\") or \"Other\")", MAIN)
        self.assertIn('const qualityOrder = ["4K / 2160p", "1080p", "720p", "SD / 480p", "Other"];', CARD)
        self.assertIn("stream-quality-separator", CARD)

    def test_picker_respects_bottom_nav(self):
        self.assertIn("inset: 0 0 var(--apollo-bottom-nav-height) 0;", CARD)

    def test_active_context_has_video_and_audio(self):
        self.assertIn("def current_player_technical_info():", MAIN)
        self.assertIn('properties": ["currentvideostream", "currentaudiostream"]', MAIN)
        self.assertIn("apollo_video_info=video_info", MAIN)
        self.assertIn("apollo_audio_info=audio_info", MAIN)
        self.assertIn("now-playing-technical", CARD)

    def test_live_detail_progress_is_patched(self):
        self.assertIn("const liveProgress =", CARD)
        self.assertIn('this.querySelector("[data-title-progress]")', CARD)
        self.assertIn("resume_position: sample.position", CARD)


if __name__ == "__main__":
    unittest.main()

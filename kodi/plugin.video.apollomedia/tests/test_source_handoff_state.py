import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")
HA = (ROOT.parent / "ha/apollo_home_assistant_prototype.yaml").read_text(encoding="utf-8")


class SourceHandoffStateTests(unittest.TestCase):
    def test_local_handoff_uses_playeropen_native_resume(self):
        block = HA.split("apollo_switch_local:", 1)[1].split("\n  apollo_play:", 1)[0]
        self.assertIn("method: Player.Open", block)
        self.assertIn("options:", block)
        self.assertIn("resume: true", block)
        self.assertIn("&resume_mode=resume", block)
        self.assertNotIn("Addons.ExecuteAddon", block)
        self.assertNotIn("&resume_mode=live", block)

    def test_local_resolver_does_not_request_live_post_avstart_seek(self):
        start = MAIN.index("def remote_play_jellyfin(")
        end = MAIN.index("\ndef ", start + 5)
        block = MAIN[start:end]
        self.assertIn('resume_mode="resume" if position > 0 else "native"', block)
        self.assertIn("tag.setResumePoint(position, duration)", block)
        self.assertIn("xbmcplugin.setResolvedUrl(HANDLE, True, item)", block)
        self.assertNotIn("xbmc.Player().play(stream, item)", block)

    def test_picker_current_requires_actual_remote_playing_file(self):
        start = MAIN.index("def remote_stream_list(")
        end = MAIN.index("\ndef ", start + 5)
        block = MAIN[start:end]
        self.assertIn("current_index = -1", block)
        self.assertIn("player.getPlayingFile() == str(selected.get(\"url\") or \"\")", block)

    def test_card_rejects_stale_active_context(self):
        self.assertIn("invalidateActiveApolloContext(expectedSource", CARD)
        self.assertIn("_activeContextNotBefore", CARD)
        self.assertIn("_expectedPlaybackSource", CARD)
        self.assertIn('expected === "remote" && !remote', CARD)
        self.assertIn('expected === "local" && remote', CARD)

    def test_source_changes_invalidate_active_context(self):
        self.assertIn('this.invalidateActiveApolloContext("remote");', CARD)
        self.assertIn('this.invalidateActiveApolloContext("local");', CARD)

    def test_local_label_is_simple(self):
        self.assertIn('const sourceLabel = !remoteApollo && activeApollo ? "LOCAL" : "";', CARD)
        self.assertNotIn('LOCAL · JELLYFIN', CARD)

    def test_picker_header_does_not_scroll_with_sources(self):
        self.assertIn("overflow: hidden;", CARD)
        self.assertIn(".stream-picker-list,", CARD)
        self.assertIn("overflow-y: auto;", CARD)


if __name__ == "__main__":
    unittest.main()

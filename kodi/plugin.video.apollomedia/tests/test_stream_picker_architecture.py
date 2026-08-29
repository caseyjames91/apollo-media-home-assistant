import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")
HA = (ROOT.parent / "apollo_home_assistant_prototype.yaml").read_text(encoding="utf-8")


class StreamPickerArchitectureTests(unittest.TestCase):
    def test_headless_stream_route_exists(self):
        self.assertIn("def remote_stream_list(", MAIN)
        self.assertIn('elif action == "remote_stream_list":', MAIN)

    def test_card_gets_opaque_remote_targets(self):
        self.assertIn('"remote_auto_target": str(remote_auto_target or "")', MAIN)
        self.assertIn('"remote_choose_target": str(remote_choose_target or "")', MAIN)
        self.assertIn("remoteAutoTarget: params.remote_auto_target", CARD)
        self.assertIn("remoteChooseTarget: params.remote_choose_target", CARD)

    def test_stream_list_never_returns_provider_url_as_file(self):
        block = MAIN.split("def remote_stream_list(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn('action="play_session_stream"', block)
        self.assertNotIn('xbmcplugin.addDirectoryItem(HANDLE, stream.get("url")', block)

    def test_live_picker_selection_preserves_position(self):
        self.assertIn("start_position=None, start_duration=None", MAIN)
        self.assertIn("source_session.update_resume(position, duration, mode)", MAIN)
        self.assertIn("apollo_play_stream:", HA)
        self.assertIn("&resume_mode=live", HA)

    def test_local_to_remote_handoff_preserves_position(self):
        self.assertIn("apollo_switch_remote:", HA)
        self.assertIn("switchNowPlayingToRemote()", CARD)
        self.assertIn("data-now-playing-switch-remote", CARD)

    def test_remote_controls_are_dynamic(self):
        self.assertIn("data-now-playing-stream-picker", CARD)
        self.assertIn("data-now-playing-try-next", CARD)
        self.assertIn("data-now-playing-flag", CARD)
        self.assertIn('const sourceLabel = !remoteApollo && activeApollo ? "LOCAL" : "";', CARD)
        self.assertNotIn('["REMOTE STREAM", activeApollo?.provider', CARD)

    def test_flag_menu_uses_existing_backend(self):
        self.assertIn('["wrong_language", "Wrong language"]', CARD)
        self.assertIn("this.config.flag_script", CARD)
        self.assertIn('params: "?action=flag_current&reason={{ reason | urlencode }}"', HA)

    def test_ha_stream_sensor_is_headless_route(self):
        self.assertIn("action=remote_stream_list", HA)
        self.assertNotIn("directory.startswith('plugin://plugin.video.apollomedia/?action=choose_external')", HA)


if __name__ == "__main__":
    unittest.main()

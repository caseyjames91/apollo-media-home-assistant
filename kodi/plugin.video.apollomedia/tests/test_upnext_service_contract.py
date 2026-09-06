import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestUpNextServiceContract(unittest.TestCase):
    def test_upnext_is_runtime_dependency(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('<import addon="service.upnext" version="1.1.9"/>', addon)

    def test_ams_direct_successor_endpoint(self):
        ams = (ROOT / "resources" / "lib" / "ams.py").read_text()
        self.assertIn("def next_episode(addon, media_id):", ams)
        self.assertIn('f"profiles/{profile_id(addon)}/media/{media_id}/next-episode"', ams)
        self.assertIn('== 404', ams)

    def test_service_uses_standard_upnext_jsonrpc_contract(self):
        service = (ROOT / "service.py").read_text()
        self.assertIn('"method": "JSONRPC.NotifyAll"', service)
        self.assertIn('"sender": "plugin.video.apollomedia.SIGNAL"', service)
        self.assertIn('"message": "upnext_data"', service)
        self.assertIn("base64.b64encode(", service)
        self.assertIn('"current_episode"', service)
        self.assertIn('"next_episode"', service)
        self.assertIn('"play_url"', service)

    def test_upnext_playback_is_explicit_beginning(self):
        service = (ROOT / "service.py").read_text()
        play_url = service.split("def _apollo_play_url(row):", 1)[1].split("\ndef _send_upnext", 1)[0]
        self.assertIn('"start_from_beginning": "1"', play_url)
        self.assertIn('"upnext_playback": "1"', play_url)
        self.assertIn('"action": "play_remote"', play_url)

    def test_upnext_parent_does_not_use_nested_playmedia(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def play_remote(p, choose=False):", 1)[1].split("\ndef current_stream_info", 1)[0]
        self.assertIn("upnext_playback =", block)
        self.assertIn("if start_from_beginning and not upnext_playback:", block)
        self.assertIn("xbmcplugin.setResolvedUrl(HANDLE, True, item)", block)

    def test_remote_upnext_waits_for_stream_validation(self):
        service = (ROOT / "service.py").read_text()
        validate = service.split("def _validate_remote(", 1)[1].split("\n    def _reject_current_stream", 1)[0]
        self.assertIn("self._maybe_prepare_upnext()", validate)
        self.assertIn("if decision:", validate)

    def test_release_version_remains_01057_until_release(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('version="0.10.57"', addon)


if __name__ == "__main__":
    unittest.main()

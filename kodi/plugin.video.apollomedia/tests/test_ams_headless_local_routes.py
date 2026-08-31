import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
REPO = Path(__file__).parents[3]

MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
CARD = (REPO / "card" / "apollo-media-card.js").read_text(encoding="utf-8")
HA = (REPO / "home-assistant-prototype.yaml").read_text(encoding="utf-8")
AMS_LIB = (ROOT / "resources" / "lib" / "ams.py").read_text(encoding="utf-8")


class AmsHeadlessLocalRouteTests(unittest.TestCase):
    def test_active_local_detection_supports_ams_path(self):
        start = MAIN.index("def remote_active_playback(")
        end = MAIN.index("def remote_series_catalog(", start)
        body = MAIN[start:end]
        self.assertIn('local.get("transport") == "ams"', body)
        self.assertIn('local.get("playback_path")', body)
        self.assertIn('source="ams"', body)
        self.assertIn("ams.resolve_playback_for_identity(", body)

    def test_ams_resolver_accepts_headless_absolute_position(self):
        start = MAIN.index("def resolved_playback_item(")
        end = MAIN.index("def play_resolved(", start)
        body = MAIN[start:end]
        self.assertIn("start_position=None", body)
        self.assertIn("start_duration=None", body)
        self.assertIn('if start_position not in (None, ""):', body)
        self.assertIn(
            "resume_mode,start_position,start_duration",
            body.replace(" ", "").replace("\n", ""),
        )

    def test_play_resolved_dispatch_forwards_start_position(self):
        start = MAIN.index('if action == "play_resolved":')
        end = MAIN.index('elif action == "play_discovery":', start)
        body = MAIN[start:end]
        self.assertIn('raw_start = values.get("start_position")', body)
        self.assertIn('raw_duration = values.get("start_duration")', body)

    def test_ams_continue_card_playback_uses_ams_identity(self):
        start = MAIN.index("def add_ams_continue_item(")
        end = MAIN.index("def remote_card_targets(", start)
        body = MAIN[start:end]
        self.assertIn('source="ams"', body)
        self.assertIn('row.get("available_locally")', body)

    def test_card_ams_continue_uses_ams_resolver(self):
        start = CARD.index("  amsContinueItem(item) {")
        end = CARD.index("  async loadAmsContinueWatching(", start)
        body = CARD[start:end]
        self.assertIn('source: "ams"', body)
        self.assertIn("item?.available_locally", body)

    def test_card_ams_continue_uses_ams_metadata(self):
        start = CARD.index("  amsContinueItem(item) {")
        end = CARD.index("  async loadAmsContinueWatching(", start)
        body = CARD[start:end]
        self.assertIn("item?.poster_url", body)
        self.assertIn("item?.backdrop_url", body)
        self.assertIn("item?.overview", body)
        self.assertIn("item?.year", body)
        self.assertIn("poster: posterUrl", body)
        self.assertIn("fanart: backdropUrl", body)
        self.assertIn("plot: overview", body)
        self.assertNotIn("ams_artwork_id", body)
        self.assertNotIn("artwork_jellyfin_item_id", body)

    def test_card_continue_watching_does_not_sync_jellyfin(self):
        start = CARD.index("  async loadAmsContinueWatching(")
        end = CARD.index("  scheduleAmsContinueWatchingLoad(", start)
        body = CARD[start:end]
        self.assertNotIn("jellyfin/sync", body)
        self.assertNotIn("sync: true", body)

    def test_kodi_continue_watching_does_not_sync_jellyfin(self):
        start = AMS_LIB.index("def continue_watching(")
        end = AMS_LIB.index("def device_key(", start)
        body = AMS_LIB[start:end]
        self.assertNotIn("jellyfin/sync", body)
        self.assertNotIn("sync_jellyfin", body)

    def test_ha_local_switch_accepts_ams_play_resolved(self):
        start = HA.index("  apollo_switch_local:")
        end = HA.index("  apollo_play:", start)
        body = HA[start:end]
        self.assertIn("action=play_resolved", body)
        self.assertIn("source=ams", body)

    def test_legacy_jellyfin_headless_route_is_removed(self):
        self.assertNotIn("def remote_play_jellyfin(", MAIN)
        self.assertNotIn('action == "remote_play_jellyfin"', MAIN)


if __name__ == "__main__":
    unittest.main()

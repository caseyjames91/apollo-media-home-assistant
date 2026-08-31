import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")
ADDON = (ROOT / "addon.xml").read_text(encoding="utf-8")

class AmsContinueWatchingTests(unittest.TestCase):
    def test_release_version(self):
        self.assertIn('version="0.9.97"', ADDON)
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

    def test_ams_is_default_continue_authority_with_safe_fallback(self):
        self.assertIn('ams_enabled: true', CARD)
        self.assertIn('this._amsContinueReady', CARD)
        self.assertIn('this.apolloItems(this.config.continue_entity)', CARD)
        self.assertIn('Apollo AMS Continue Watching unavailable; using Home Assistant fallback', CARD)

    def test_card_uses_authenticated_home_assistant_ingress(self):
        self.assertIn('endpoint: "/ingress/session"', CARD)
        self.assertIn('endpoint: "/ingress/panels"', CARD)
        self.assertIn('endpoint: `/addons/${slug}/info`', CARD)
        self.assertIn('document.cookie = `ingress_session=', CARD)
        self.assertIn('credentials: "same-origin"', CARD)

    def test_profile_scoped_continue_endpoint(self):
        self.assertIn('profiles/${encodeURIComponent(profileId)}/continue-watching', CARD)
        self.assertIn('ams_profile_id', CARD)
        self.assertIn('ams_profile', CARD)

    def test_playback_stays_on_existing_player_path(self):
        self.assertIn('player_entity: playerEntity', CARD)
        self.assertIn('this.config.play_script', CARD)
        self.assertIn('this.apolloPluginUrl("play_resolved"', CARD)
        self.assertIn('this.apolloPluginUrl("play_external"', CARD)

if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = ROOT.parent / "apollo-media-card.js"

class CardRefreshFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CARD.read_text(encoding="utf-8")

    def test_ha_script_entity_is_running_authority(self):
        self.assertIn("refreshScriptRunning(hass = this._hass)", self.source)
        self.assertIn('String(this.refreshScriptEntity(hass)?.state || "").toLowerCase() === "on"', self.source)

    def test_completion_requires_ha_on_to_off_transition(self):
        self.assertIn('if (previous === "on" && current !== "on")', self.source)
        self.assertIn("this._refreshSuccessUntil = Date.now() + 2800", self.source)

    def test_refresh_survives_rerender(self):
        self.assertIn('${this.refreshVisualState() === "success" ? "mdi:check" : "mdi:refresh"}', self.source)
        self.assertIn('this.observeMediaRefreshState(hass);', self.source)

    def test_running_button_is_disabled(self):
        self.assertIn('button.disabled = running', self.source)
        self.assertIn('aria-busy', self.source)

    def test_click_does_not_use_page_local_timeout_spinner(self):
        self.assertIn('this.beginMediaRefresh()', self.source)
        self.assertNotIn('window.setTimeout(() => refreshBtn.classList.remove("refreshing"), 800)', self.source)

    def test_success_icon_is_green(self):
        self.assertIn(".refresh-action.refresh-success", self.source)
        self.assertIn("color: #4ade80", self.source)

if __name__ == "__main__":
    unittest.main()

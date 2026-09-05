import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestRebuiltApolloContract(unittest.TestCase):
    def test_release_version(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('version="0.10.52"', addon)

    def test_root_is_navigation_only(self):
        main = (ROOT / "main.py").read_text()
        home = main.split("def home():", 1)[1].split("\ndef ", 1)[0]
        for label in ("Current Stream Info", "Try Next Stream", "Flag Current Stream",
                      "Link TorBox", "Relink TorBox", "Detect Device Compatibility"):
            self.assertNotIn(f'action_item("{label}', home)
        self.assertIn('ListItem(label="Settings")', home)

    def test_playback_tools_remain_contextual(self):
        main = (ROOT / "main.py").read_text()
        self.assertIn('"Current Stream Info", f"RunPlugin(', main)
        self.assertIn('"Try Next Stream", f"RunPlugin(', main)
        self.assertIn('"Flag Current Stream", f"RunPlugin(', main)

if __name__ == "__main__":
    unittest.main()

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SETTINGS = (ROOT / "resources/settings.xml").read_text(encoding="utf-8")
STRINGS = (ROOT / "resources/language/resource.language.en_gb/strings.po").read_text(encoding="utf-8")

class SettingsLocalizationTests(unittest.TestCase):
    def test_every_settings_string_id_is_defined(self):
        ids = set(re.findall(r'(?:label|help|heading)="(\d{5})"', SETTINGS))
        defined = set(re.findall(r'msgctxt "#(\d{5})"', STRINGS))
        self.assertEqual(ids - defined, set())

    def test_core_settings_are_human_readable(self):
        for label in [
            "Jellyfin server URL",
            "Jellyfin access token",
            "TorBox API token",
            "Enable Comet",
            "Allow 2160p / 4K",
            "Detected device",
        ]:
            self.assertIn(f'msgid "{label}"', STRINGS)

    def test_language_catalog_is_packaged_under_kodi_resource_path(self):
        self.assertTrue((ROOT / "resources/language/resource.language.en_gb/strings.po").is_file())

if __name__ == "__main__":
    unittest.main()

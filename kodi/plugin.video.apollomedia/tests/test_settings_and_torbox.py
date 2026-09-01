import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

class TestSettingsAndTorBox(unittest.TestCase):
    def test_settings_xml_and_actions(self):
        path = ROOT / "resources" / "settings.xml"
        ET.parse(path)
        text = path.read_text()
        self.assertIn("action=link_torbox", text)
        self.assertIn("action=detect_compatibility", text)

    def test_qr_asset_and_dialog(self):
        self.assertTrue((ROOT / "resources/media/torbox-link-qr.png").is_file())
        dialog = ROOT / "resources/skins/Default/1080i/TorBoxLink.xml"
        ET.parse(dialog)
        self.assertIn("torbox-link-qr.png", dialog.read_text())

    def test_torbox_link_target(self):
        text = (ROOT / "resources/lib/torbox.py").read_text()
        self.assertIn("https://tor.box/link", text)
        self.assertIn("TorBoxLinkDialog", text)

if __name__ == "__main__":
    unittest.main()

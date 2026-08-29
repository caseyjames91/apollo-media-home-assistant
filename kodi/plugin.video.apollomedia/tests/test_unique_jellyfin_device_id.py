import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JF = (ROOT / "resources/lib/jellyfin.py").read_text(encoding="utf-8")

class UniqueJellyfinDeviceIdTests(unittest.TestCase):
    def test_fixed_device_id_removed(self):
        self.assertNotIn('DEVICE_ID = "apollo-kodi"', JF)
        self.assertIn('DEVICE_ID_FILENAME = "jellyfin_device_id.txt"', JF)
        self.assertIn('"apollo-kodi-" + uuid.uuid4().hex', JF)

    def test_all_jellyfin_device_id_uses_are_persistent(self):
        self.assertIn('f\'DeviceId="{get_device_id()}"\'', JF)
        self.assertIn('"DeviceId": get_device_id()', JF)

if __name__ == "__main__":
    unittest.main()

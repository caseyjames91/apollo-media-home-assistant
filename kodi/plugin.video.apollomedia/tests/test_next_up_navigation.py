import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKodiNextUpContract(unittest.TestCase):
    def test_ams_client_owns_next_up_request(self):
        ams = (ROOT / "resources" / "lib" / "ams.py").read_text()
        self.assertIn("def next_up(addon):", ams)
        self.assertIn(
            'f"profiles/{profile_id(addon)}/next-up"',
            ams,
        )

    def test_home_exposes_next_up_navigation(self):
        main = (ROOT / "main.py").read_text()
        home = main.split("def home():", 1)[1].split("\ndef ", 1)[0]
        self.assertIn('folder("Next Up", url("next_up"))', home)

    def test_next_up_reuses_canonical_playable_media(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def next_up():", 1)[1].split(
            "\ndef _canonical_detail_target", 1
        )[0]

        self.assertIn("rows = ams.next_up(ADDON)", block)
        self.assertIn("playable_media(", block)
        self.assertIn('"series"', block)
        self.assertIn('row.get("position_seconds")', block)
        self.assertIn('row.get("duration_seconds")', block)
        self.assertNotIn("play_remote(", block)
        self.assertNotIn("find_streams(", block)

    def test_next_up_route_is_dispatched(self):
        main = (ROOT / "main.py").read_text()
        self.assertIn('elif action == "next_up":', main)
        self.assertIn("        next_up()", main)

    def test_next_up_does_not_change_release_version(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('version="0.10.60"', addon)


if __name__ == "__main__":
    unittest.main()

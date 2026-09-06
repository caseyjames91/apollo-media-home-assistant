import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKodiSkinPresentationMetadata(unittest.TestCase):
    def test_art_exposes_standard_landscape_role(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def art(row):", 1)[1].split("\ndef ", 1)[0]

        self.assertIn('result["poster"] = poster', block)
        self.assertIn('result["fanart"] = fanart', block)
        self.assertIn('result["landscape"] = landscape', block)

    def test_episode_thumb_prefers_landscape(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def art(row):", 1)[1].split("\ndef ", 1)[0]

        self.assertIn('media_type == "episode" and landscape', block)
        self.assertIn('result["thumb"] = landscape', block)

    def test_common_metadata_exposes_tmdb_and_media_type(self):
        main = (ROOT / "main.py").read_text()
        block = main.split("def apply_common(", 1)[1].split("\ndef ", 1)[0]

        self.assertIn('tag.setUniqueID(tmdb_id, "tmdb")', block)
        self.assertIn('"show": "tvshow"', block)
        self.assertIn('"episode": "episode"', block)
        self.assertIn("tag.setMediaType(kodi_media_type)", block)

    def test_presentation_change_does_not_bump_release(self):
        addon = (ROOT / "addon.xml").read_text()
        self.assertIn('version="0.10.61"', addon)


if __name__ == "__main__":
    unittest.main()

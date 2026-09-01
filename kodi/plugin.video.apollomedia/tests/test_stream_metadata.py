import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resources.lib.stream_metadata import parse, technical_info


def stream(title, description=""):
    return SimpleNamespace(
        title=title,
        description=description,
        provider="torrentio",
        url="x",
    )


class StreamMetadataTests(unittest.TestCase):
    def test_ps4k_does_not_promote_resolution(self):
        meta = parse(
            stream(
                "Toy Story 5 (2026) "
                "(1080p PS4K BluRay x265 10-bit SDR AAC 5.1).mkv"
            )
        )
        self.assertEqual(meta.resolution, 1080)
        self.assertEqual(meta.source, "bluray")

    def test_real_4k_is_2160(self):
        self.assertEqual(
            parse(stream("Movie.4K.WEB.x265.mkv")).resolution,
            2160,
        )

    def test_structured_video_metadata(self):
        meta = parse(
            stream(
                "Movie.2160p.DV.WEB-DL.HEVC."
                "TrueHD.Atmos.7.1.mkv"
            )
        )
        self.assertEqual(meta.resolution, 2160)
        self.assertEqual(meta.dynamic_range, "dolby_vision")
        self.assertEqual(meta.video_codec, "hevc")
        self.assertEqual(meta.audio_codec, "truehd")
        self.assertTrue(meta.atmos)
        self.assertEqual(meta.channels, "7.1")

    def test_subtitle_languages_are_not_audio(self):
        meta = parse(
            stream(
                "Movie.(Spanish.English.Subs)."
                "WEB-DL.1080p.x264-EAC3.mkv"
            )
        )
        self.assertEqual(meta.languages, ())

    def test_explicit_audio_language_is_preserved(self):
        meta = parse(
            stream("Movie.English.WEB-DL.1080p.x264-EAC3.mkv")
        )
        self.assertEqual(meta.languages, ("english",))

    def test_cam_is_structured_flag(self):
        self.assertTrue(
            parse(stream("Movie.1080p.HDCAM.mkv")).low_quality_capture
        )

    def test_technical_info_uses_same_resolution_parser(self):
        info = technical_info(
            "Toy Story 5 (2026) "
            "(1080p PS4K BluRay x265 10-bit SDR AAC 5.1).mkv"
        )
        self.assertEqual(info["quality"], "1080p")
        self.assertIn("HEVC", info["video"])
        self.assertIn("5.1", info["audio"])

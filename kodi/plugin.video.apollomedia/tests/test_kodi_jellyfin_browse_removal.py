import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class KodiJellyfinBrowseRemovalTests(unittest.TestCase):
    def test_legacy_jellyfin_modules_are_deleted(self):
        self.assertFalse((ROOT / "resources/lib/jellyfin.py").exists())
        self.assertFalse((ROOT / "resources/lib/media_service.py").exists())

    def test_main_has_no_direct_jellyfin_browse_dependency(self):
        forbidden = (
            "from resources.lib.jellyfin import",
            "from resources.lib.media_service import",
            "JellyfinClient",
            "MediaService(",
            "require_jellyfin(",
            "media_service()",
            'action="seasons"',
            'action="episodes"',
        )
        for marker in forbidden:
            self.assertNotIn(marker, MAIN)

    def test_library_routes_are_ams_owned(self):
        library_start = MAIN.index("def library(")
        series_start = MAIN.index("def series_library(", library_start)
        discovery_start = MAIN.index("def discovery_seasons(", series_start)
        movie_body = MAIN[library_start:series_start]
        show_body = MAIN[series_start:discovery_start]
        self.assertIn('ams.media(ADDON, "movie", available_locally=True)', movie_body)
        self.assertIn("_ams_local_series_rows()", show_body)
        self.assertNotIn("jellyfin", (movie_body + show_body).lower())

    def test_headless_movie_catalog_is_apollo_owned(self):
        start = MAIN.index("def remote_movie_catalog(")
        end = MAIN.index("def remote_empty_feed(", start)
        body = MAIN[start:end]
        self.assertIn("popular_movies()", body)
        self.assertIn("remote_ams_library", body)
        self.assertNotIn("jellyfin", body.lower())


if __name__ == "__main__":
    unittest.main()

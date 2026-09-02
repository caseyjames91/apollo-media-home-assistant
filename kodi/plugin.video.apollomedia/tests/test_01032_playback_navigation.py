import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / 'main.py').read_text()
SERVICE = (ROOT / 'service.py').read_text()
SOURCES = (ROOT / 'resources/lib/sources.py').read_text()
SESSION = (ROOT / 'resources/lib/source_session.py').read_text()


class PlaybackNavigation032(unittest.TestCase):
    def test_provider_cached_rows_restored(self):
        self.assertIn('elif provider_asserted:', SOURCES)
        self.assertNotIn('elif provider_asserted and key:', SOURCES)

    def test_implausible_duration_falls_through(self):
        self.assertIn('implausible_duration', SERVICE)
        self.assertIn('duration_is_implausible', SERVICE)

    def test_episode_has_go_to_series(self):
        self.assertIn('"Go to Series"', MAIN)
        self.assertIn('"go_to_series"', MAIN)

    def test_air_date_uses_infotag_title(self):
        self.assertIn('tag.setTitle(display_label)', MAIN)

    def test_session_preserves_cache_state(self):
        self.assertIn('"cached": getattr(stream, "cached", None)', SESSION)

    def test_python_parses(self):
        for path in (
            ROOT / 'main.py',
            ROOT / 'service.py',
            ROOT / 'resources/lib/ams.py',
            ROOT / 'resources/lib/sources.py',
            ROOT / 'resources/lib/source_session.py',
        ):
            ast.parse(path.read_text())


if __name__ == '__main__':
    unittest.main()

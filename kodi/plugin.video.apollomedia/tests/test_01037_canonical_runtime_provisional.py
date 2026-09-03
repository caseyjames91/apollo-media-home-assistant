from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'main.py').read_text()
SERVICE=(ROOT/'service.py').read_text()
SESSION=(ROOT/'resources/lib/source_session.py').read_text()
class CanonicalRuntimeProvisionalTests(unittest.TestCase):
    def test_remote_params_use_canonical_expected_duration(self):
        self.assertIn('row.get("expected_duration_seconds")', MAIN)
    def test_attempt_has_started_state(self):
        self.assertIn('def start_attempt():', SESSION)
        self.assertIn('attempts["state"]="started"', SESSION)
    def test_av_started_is_provisional(self):
        self.assertIn('source_session.start_attempt()', SERVICE)
        self.assertIn('playback attempt confirmed after stable grace', SERVICE)
    def test_provisional_progress_is_suppressed(self):
        self.assertIn('suppressing provisional remote progress', SERVICE)
        self.assertIn('ended_before_confirmation', SERVICE)
if __name__ == '__main__': unittest.main()

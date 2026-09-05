import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestProviderEngineContract(unittest.TestCase):
    def test_provider_modules_present(self):
        for name in ("sources.py", "source_session.py", "compatibility.py", "torbox.py", "stream_dialog.py"):
            self.assertTrue((ROOT / "resources/lib" / name).is_file())

    def test_manual_playback_handoff(self):
        main = (ROOT / "main.py").read_text()
        self.assertIn('play_url = url("play_session_stream", index=index)', main)
        self.assertIn('PlayMedia(" + play_url', main)

    def test_profile_cache_present(self):
        ams = (ROOT / "resources/lib/ams.py").read_text()
        self.assertIn("_profile_id_cache", ams)
        self.assertIn("_progress_index_cache", ams)

if __name__ == "__main__":
    unittest.main()

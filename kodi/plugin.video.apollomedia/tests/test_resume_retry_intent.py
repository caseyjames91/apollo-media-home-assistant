import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "service.py").read_text(encoding="utf-8")


class ResumeRetryIntentTests(unittest.TestCase):
    def test_source_session_starts_with_native_resume_intent(self):
        self.assertIn("resume_position, resume_duration = ams.resume(", MAIN)
        self.assertIn("resume_position=resume_position", MAIN)
        self.assertIn("resume_duration=resume_duration", MAIN)
        self.assertIn('resume_mode="native"', MAIN)

    def test_retry_reuses_resolved_resume_intent(self):
        self.assertIn(
            'resume_mode = str(session.get("resume_mode") or "native")',
            MAIN,
        )
        self.assertIn('item.setProperty("StartOffset", str(position))', MAIN)
        self.assertIn('item.setProperty("StartOffset", "0")', MAIN)

    def test_service_captures_native_resume_choice_once(self):
        self.assertIn("def _capture_resume_intent(self):", SERVICE)
        self.assertIn(
            'source_session.update_resume(0, 0, "beginning")',
            SERVICE,
        )
        self.assertIn('"fixed",', SERVICE)
        self.assertIn("self._capture_resume_intent()", SERVICE)


if __name__ == "__main__":
    unittest.main()

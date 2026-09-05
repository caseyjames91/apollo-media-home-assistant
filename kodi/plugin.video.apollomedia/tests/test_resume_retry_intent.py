import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "service.py").read_text(encoding="utf-8")


class ResumeRetryIntentTests(unittest.TestCase):
    def test_ams_owns_initial_resume_decision(self):
        self.assertIn("resume_position, resume_duration, _watched = ams.progress_for(", MAIN)
        self.assertIn(
            'resume_mode = "fixed" if resume_position > 0 else "beginning"',
            MAIN,
        )
        self.assertNotIn('resume_mode="native"', MAIN)

    def test_explicit_beginning_overrides_ams_resume(self):
        self.assertIn('p.get("start_from_beginning")', MAIN)
        self.assertIn('resume_mode = "beginning"', MAIN)
        self.assertIn('"Play from beginning"', MAIN)

    def test_fixed_resume_uses_start_offset(self):
        self.assertIn(
            'resume_mode = str(session.get("resume_mode") or "beginning")',
            MAIN,
        )
        self.assertIn('item.setProperty("StartOffset", str(position))', MAIN)

    def test_all_apollo_handoffs_force_noresume(self):
        self.assertIn('PlayMedia(" + play_url + ",noresume)', MAIN)
        self.assertIn('PlayMedia({play_url},noresume)', SERVICE)
        self.assertNotIn('PlayMedia(" + play_url + ")', MAIN)
        self.assertNotIn('PlayMedia({play_url})', SERVICE)

    def test_service_no_longer_infers_native_resume_choice(self):
        self.assertNotIn("def _capture_resume_intent(self):", SERVICE)
        self.assertNotIn("self._capture_resume_intent()", SERVICE)


if __name__ == "__main__":
    unittest.main()

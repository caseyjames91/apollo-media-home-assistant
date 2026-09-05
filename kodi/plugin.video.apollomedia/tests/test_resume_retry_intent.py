import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "service.py").read_text(encoding="utf-8")


class ResumeRetryIntentTests(unittest.TestCase):
    def test_native_kodi_choice_owns_initial_resume_intent(self):
        self.assertIn("if HANDLE >= 0 and len(sys.argv) > 3:", MAIN)
        self.assertIn('if native_token == "resume:true":', MAIN)
        self.assertIn("native_resume = True", MAIN)
        self.assertIn("resume_position, resume_duration, _watched = ams.progress_for(", MAIN)
        self.assertIn(
            'resume_mode = "fixed" if resume_position > 0 else "beginning"',
            MAIN,
        )

    def test_native_beginning_does_not_apply_ams_resume(self):
        self.assertIn('elif native_token == "resume:false":', MAIN)
        self.assertIn("native_resume = False", MAIN)
        self.assertIn(
            "if start_from_beginning or native_resume is False:",
            MAIN,
        )
        self.assertIn(
            "resume_position, resume_duration = 0.0, 0.0",
            MAIN,
        )

    def test_runplugin_without_native_choice_keeps_ams_fallback(self):
        self.assertIn("native_resume = None", MAIN)
        self.assertIn("if HANDLE >= 0 and len(sys.argv) > 3:", MAIN)
        self.assertNotIn("if start_from_beginning or not native_resume:", MAIN)

    def test_explicit_beginning_overrides_ams_resume(self):
        self.assertIn('p.get("start_from_beginning")', MAIN)
        self.assertIn('resume_mode = "beginning"', MAIN)
        self.assertIn('"Play from beginning"', MAIN)

    def test_fixed_resume_uses_resolved_resume_point(self):
        self.assertIn(
            'resume_mode = str(session.get("resume_mode") or "beginning")',
            MAIN,
        )
        self.assertIn(
            'resume_duration = max(0.0, float(session.get("resume_duration") or 0))',
            MAIN,
        )
        self.assertIn('tag.setResumePoint(position, resume_duration)', MAIN)
        self.assertNotIn('item.setProperty("StartOffset", str(position))', MAIN)

    def test_all_apollo_handoffs_force_noresume(self):
        self.assertIn('PlayMedia(" + play_url + ",noresume)', MAIN)
        self.assertIn('PlayMedia({play_url},noresume)', SERVICE)
        self.assertNotIn('PlayMedia(" + play_url + ")', MAIN)
        self.assertNotIn('PlayMedia({play_url})', SERVICE)

    def test_normal_remote_activation_uses_session_handoff(self):
        play_remote = MAIN.split("def play_remote(", 1)[1].split(
            "\ndef current_stream_info(", 1
        )[0]

        self.assertIn(
            'play_url = url("play_session_stream", index=index)',
            play_remote,
        )
        self.assertIn(
            'PlayMedia(" + play_url + ",noresume)',
            play_remote,
        )
        self.assertNotIn(
            '_resolve_remote(stream, p)',
            play_remote,
        )

    def test_service_no_longer_infers_native_resume_choice(self):
        self.assertNotIn("def _capture_resume_intent(self):", SERVICE)
        self.assertNotIn("self._capture_resume_intent()", SERVICE)


if __name__ == "__main__":
    unittest.main()

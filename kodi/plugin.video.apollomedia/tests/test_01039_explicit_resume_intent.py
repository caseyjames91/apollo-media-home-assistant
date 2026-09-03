import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
M=(ROOT/"main.py").read_text()
S=(ROOT/"service.py").read_text()

class ResumeIntent039(unittest.TestCase):
 def test_choice_is_explicit_before_stream(self):
  self.assertIn('f"Resume from {resume_label}?"',M)
  self.assertIn('nolabel="Play from beginning"',M)
  self.assertIn('yeslabel="Resume"',M)
  self.assertIn('resume_mode=resume_mode',M)
 def test_beginning_is_session_state(self):
  self.assertIn('resume_mode = "beginning"',M)
  self.assertIn('resume_position, resume_duration = 0.0, 0.0',M)
 def test_fixed_is_forced_offset_not_kodi_bookmark(self):
  block=M[M.index("def _resolve_remote"):M.index("def _save_source_session")]
  self.assertIn('item.setProperty("StartOffset", str(position))',block)
  self.assertNotIn("setResumePoint",block)
 def test_old_runtime_heuristic_cannot_override_explicit_choice(self):
  self.assertIn('if str(session.get("resume_mode") or "native") != "native":',S)
 def test_fallback_reuses_session(self):
  self.assertIn('_plugin_url("play_session_stream",index=index)',S)

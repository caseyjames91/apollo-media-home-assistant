import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
M=(ROOT/"main.py").read_text()
class SingleResumeOwner040(unittest.TestCase):
 def test_progress_metadata_remains(self):
  b=M[M.index("def playable_media("):M.index("\ndef home():")]
  self.assertIn('item.setProperty("IsPlayable", "false")',b)
  self.assertIn("tag.setResumePoint(position, duration)",b)
 def test_apollo_explicit_choice_remains(self):
  self.assertIn('f"Resume from {resume_label}?"',M)
  self.assertIn('resume_mode = "beginning"',M)
  self.assertIn('resume_mode = "fixed"',M)
 def test_resolver_uses_start_offset(self):
  b=M[M.index("def _resolve_remote("):M.index("\ndef _save_source_session(")]
  self.assertIn('item.setProperty("StartOffset", str(position))',b)
  self.assertNotIn("setResumePoint",b)

import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
M=(ROOT/"main.py").read_text()
class CommandActivation041(unittest.TestCase):
 def playable(self): return M[M.index("def playable_media("):M.index("\ndef home():")]
 def command(self): return M[M.index("def play_remote_command("):M.index("\ndef play_remote(")]
 def resolver(self): return M[M.index("def play_remote("):M.index("\ndef go_to_season(")]
 def test_row_is_builtin_command_not_plugin_media_path(self):
  b=self.playable()
  self.assertIn('"RunPlugin(" + remote_target + ")"',b)
  self.assertIn('"play_remote_command"',b)
  self.assertNotIn('launch="1"',b)
 def test_command_owns_resume_session_then_launches_resolver(self):
  b=self.command()
  self.assertIn("_save_source_session(streams, p)",b)
  self.assertIn('"PlayMedia(" + url("play_session_stream", index=index) + ")"',b)
  self.assertNotIn("setResolvedUrl",b)
 def test_direct_play_remote_remains_resolver(self):
  b=self.resolver()
  self.assertIn("_resolve_remote(stream, p)",b)
  self.assertNotIn('p.get("launch")',b)
 def test_manual_picker_still_launches_session_stream(self):
  b=self.resolver()
  self.assertIn("if choose:",b)
  self.assertIn("_choose_stream_dialog()",b)
  self.assertIn('"PlayMedia(" + url("play_session_stream", index=index) + ")"',b)
 def test_dispatch_separates_command_and_resolver(self):
  self.assertIn('elif action == "play_remote_command":',M)
  self.assertIn("play_remote_command(p)",M)
  self.assertIn('elif action == "play_remote":',M)
  self.assertIn("play_remote(p,False)",M)

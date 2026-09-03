import ast,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
M=(ROOT/"main.py").read_text(); S=(ROOT/"service.py").read_text()
class Canonical033(unittest.TestCase):
 def test_library_uses_canonical_show(self): self.assertIn('url("discovery_show", tmdb=tmdb',M)
 def test_season_metadata(self):
  self.assertIn('"backdrop_url": details.get("backdrop_url")',M); self.assertIn('row.get("overview") or details.get("overview")',M)
 def test_episode_navigation(self):
  self.assertIn('"Go to Season"',M); self.assertIn("def go_to_season(p):",M); self.assertIn('"go_to_series"',M)
 def test_resume_intent_survives_fallback(self):
  self.assertIn('resume_mode = "beginning"',M); self.assertIn('resume_mode = "fixed"',M); self.assertIn('item.setProperty("StartOffset", str(position))',M); self.assertIn("def _capture_resume_intent(self):",S)
 def test_parse(self): ast.parse(M); ast.parse(S)

import json, os, sys, tempfile, types, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
_profile=tempfile.mkdtemp(prefix="apollo-fallback-")
x=types.ModuleType("xbmcvfs"); x.translatePath=lambda value:_profile; sys.modules.setdefault("xbmcvfs",x)
from resources.lib import source_session
def row(title,quality,key): return {"title":title,"url":"https://example/"+key,"provider":"torrentio","quality":quality,"stream_key":key,"release_aliases":[key]}
class Tests(unittest.TestCase):
 def setUp(self):
  try: os.unlink(source_session._path())
  except FileNotFoundError: pass
  d={"created":source_session.time.time(),"index":1,"imdb_id":"tt1","media_type":"movie","season":0,"episode":0,"title":"Test","streams":[row("4K","2160p","4k"),row("A","1080p","a"),row("B","1080p","b"),row("C","720p","c")],"flags":[],"attempts":{"state":"idle","failed_keys":[]}}
  with open(source_session._path(),"w") as f: json.dump(d,f)
 def test_confirm(self):
  source_session.begin_attempt(1); self.assertEqual(source_session.attempt_state()["state"],"requested"); source_session.confirm_attempt(); self.assertEqual(source_session.attempt_state()["state"],"confirmed")
 def test_failure_advances_same_resolution(self):
  source_session.begin_attempt(1); d,s=source_session.fail_attempt("test"); self.assertEqual(d["index"],2); self.assertEqual(s["stream_key"],"b")
 def test_failure_not_flag(self):
  source_session.begin_attempt(1); d,_=source_session.fail_attempt("test"); self.assertEqual(d["flags"],[]); self.assertTrue(d["attempts"]["failed_keys"])
if __name__=="__main__": unittest.main()

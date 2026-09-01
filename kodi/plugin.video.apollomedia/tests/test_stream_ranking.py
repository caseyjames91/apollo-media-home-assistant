import sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
http=types.ModuleType("resources.lib.http"); http.get_json=lambda *a,**k:{}
sys.modules.setdefault("resources.lib.http",http)
from resources.lib.sources import Stream,filter_reason,rank_streams
class Tests(unittest.TestCase):
    def test_cam(self): self.assertEqual(filter_reason(Stream("Movie.1080p.HDCAM","x")),"cam_or_telesync")
    def test_resolution(self): self.assertEqual(filter_reason(Stream("Movie.2160p.WEB-DL","x"),{"allow_2160p":False}),"allow_2160p")
    def test_language_filter(self): self.assertEqual(filter_reason(Stream("Movie.1080p.SPANISH.WEB-DL","x"),{"excluded_languages":"spanish"}),"excluded_language")
    def test_unknown_language(self): self.assertIsNone(filter_reason(Stream("Movie.1080p.WEB-DL","x"),{"allowed_languages":"english"}))
    def test_quality_beats_provider(self):
        x=[Stream("Movie.480p.WEB-DL","a",provider="debridio"),Stream("Movie.1080p.WEB-DL","b",provider="torrentio")]
        self.assertEqual(rank_streams(x,{"provider_priority":"debridio,torrentio"})[0].url,"b")
    def test_provider_tiebreak(self):
        x=[Stream("Movie.1080p.WEB-DL","a",provider="torrentio"),Stream("Movie.1080p.WEB-DL","b",provider="debridio")]
        self.assertEqual(rank_streams(x,{"provider_priority":"debridio,torrentio"})[0].url,"b")
    def test_language_tiebreak(self):
        x=[Stream("Movie.1080p.SPANISH.WEB-DL","a",provider="debridio"),Stream("Movie.1080p.ENGLISH.WEB-DL","b",provider="torrentio")]
        self.assertEqual(rank_streams(x,{"preferred_languages":"english,spanish","provider_priority":"debridio,torrentio"})[0].url,"b")
    def test_deterministic(self):
        x=[Stream("Z.Movie.1080p.WEB-DL","z",provider="torrentio"),Stream("A.Movie.1080p.WEB-DL","a",provider="torrentio")]
        self.assertEqual([s.url for s in rank_streams(x,{})],[s.url for s in rank_streams(reversed(x),{})])

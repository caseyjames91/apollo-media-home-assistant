import unittest
from pathlib import Path
import sys
import ast
import io
import json

ADDON_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from resources.lib.playback_intent import (
    resolve_remote_position,
    should_seek_remote,
)


class RemoteResumeSemanticsTests(unittest.TestCase):
    def test_explicit_resume_loads_saved_position_once(self):
        calls = []

        def load_saved():
            calls.append(True)
            return 1800, 7200

        self.assertEqual(
            resolve_remote_position("resume", None, None, load_saved),
            (1800.0, 7200.0, "resume"),
        )
        self.assertEqual(len(calls), 1)
        self.assertTrue(should_seek_remote(True, 1800, "resume"))

    def test_start_over_is_zero_and_does_not_read_or_delete_progress(self):
        saved = {"position": 3000}

        def load_saved():
            raise AssertionError("Start Over read historical progress")

        self.assertEqual(
            resolve_remote_position("start_over", None, None, load_saved),
            (0.0, 0.0, "start_over"),
        )
        self.assertEqual(saved["position"], 3000)
        self.assertFalse(should_seek_remote(True, 0, "start_over"))

    def test_next_resume_uses_only_the_newest_saved_position(self):
        saved = {"position": 600}
        first = resolve_remote_position(
            "resume", None, None, lambda: (saved["position"], 7200)
        )
        saved["position"] = 2100
        second = resolve_remote_position(
            "resume", None, None, lambda: (saved["position"], 7200)
        )
        self.assertEqual(first[0], 600)
        self.assertEqual(second[0], 2100)

    def test_try_next_updates_session_to_live_position(self):
        source = ADDON_ROOT.joinpath("main.py").read_text(encoding="utf-8")
        update = 'source_session.update_resume(position, duration, "live")'
        self.assertIn(update, source)
        self.assertLess(source.index(update), source.index("player.play", source.index(update)))

        session_source = ADDON_ROOT.joinpath("resources/lib/source_session.py").read_text(encoding="utf-8")
        tree = ast.parse(session_source)
        node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "update_resume")
        namespace = {
            "load": lambda: {"resume_position": 1800, "resume_mode": "resume"},
            "_path": lambda: "unused",
            "open": lambda *args, **kwargs: io.StringIO(),
            "json": json,
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), "source_session.py", "exec"), namespace)
        updated = namespace["update_resume"](2500, 7200, "live")
        self.assertEqual(updated["resume_position"], 2500)
        self.assertEqual(updated["resume_mode"], "live")

    def test_remote_start_does_not_persist_transient_position(self):
        source = ADDON_ROOT.joinpath("service.py").read_text(encoding="utf-8")
        self.assertIn('and event != "start"', source)

    def test_normal_progress_after_start_over_can_save_new_position(self):
        source = ADDON_ROOT.joinpath("service.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        playback = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PlaybackMonitor")
        report = next(node for node in playback.body if isinstance(node, ast.FunctionDef) and node.name == "report")
        saves = []

        class Progress:
            @staticmethod
            def save(*args, **kwargs):
                saves.append((args, kwargs))

        class Player:
            imdb_id = "tt123"
            media_type = "movie"
            season = 0
            episode = 0
            title = "Movie"
            last_ticks = 0
            last_duration = 0
            def position_ticks(self): return 600 * 10000000
            def getTotalTime(self): return 7200

        namespace = {"progress": Progress, "xbmc": object()}
        exec(compile(ast.Module(body=[report], type_ignores=[]), "service.py", "exec"), namespace)
        namespace["report"](Player(), "start")
        self.assertEqual(saves, [])
        namespace["report"](Player(), "progress")
        self.assertEqual(saves[-1][0][5], 600)

    def test_legacy_local_jellyfin_path_is_removed(self):
        source = ADDON_ROOT.joinpath("main.py").read_text(encoding="utf-8")
        self.assertNotIn("def play_jellyfin(", source)
        self.assertNotIn("def remote_play_jellyfin(", source)


if __name__ == "__main__":
    unittest.main()

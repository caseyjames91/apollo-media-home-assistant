import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "service.py"


class FakePlayer:
    def __init__(self):
        self._time = 0.0
        self._duration = 0.0
        self.stopped = False

    def getTime(self):
        return self._time

    def getTotalTime(self):
        return self._duration

    def stop(self):
        self.stopped = True


class FakeDialog:
    def notification(self, *args, **kwargs):
        pass


def load_monitor_player():
    tree = ast.parse(
        SERVICE.read_text(encoding="utf-8"),
        filename=str(SERVICE),
    )
    wanted = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MonitorPlayer"
    )

    module = ast.Module(body=[wanted], type_ignores=[])
    ast.fix_missing_locations(module)

    executed = []

    xbmc = types.SimpleNamespace(
        Player=FakePlayer,
        LOGWARNING=1,
        LOGERROR=2,
        log=lambda *args, **kwargs: None,
        executebuiltin=lambda value: executed.append(value),
    )

    ns = {
        "xbmc": xbmc,
        "xbmcgui": types.SimpleNamespace(Dialog=FakeDialog),
        "ADDON": object(),
        "ams": types.SimpleNamespace(),
        "source_session": types.SimpleNamespace(),
        "duration_valid": lambda actual, expected: None,
        "report_async": lambda *args, **kwargs: None,
    }

    exec(compile(module, str(SERVICE), "exec"), ns)
    return ns["MonitorPlayer"], ns, executed


class RemoteProgressGateTests(unittest.TestCase):
    def make_player(self):
        MonitorPlayer, ns, executed = load_monitor_player()
        player = MonitorPlayer()
        player.canonical_id = "episode:test"
        player.imdb = "tt0096697"
        player.media_type = "series"
        player.season = 1
        player.episode = 1
        player.title = "Simpsons Roasting on an Open Fire"
        player._time = 300.0
        player._duration = 1395.0
        return player, ns, executed

    def test_unvalidated_remote_never_reports_progress(self):
        player, ns, _ = self.make_player()
        reports = []

        player.playback_mode = "remote"
        player.identity_ready = False
        player.validated = False

        ns["report_async"] = lambda *args, **kwargs: reports.append(args)

        player.emit()

        self.assertFalse(player.validated)
        self.assertEqual(reports, [])

    def test_valid_remote_becomes_validated_then_reports_progress(self):
        player, ns, _ = self.make_player()
        reports = []

        player.playback_mode = "remote"
        player.identity_ready = True
        player.expected_duration = 1395.0
        player.validated = False

        ns["duration_valid"] = lambda actual, expected: True
        ns["report_async"] = lambda *args, **kwargs: reports.append(args)

        player.emit()

        self.assertTrue(player.validated)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][-2:], (300.0, 1395.0))

    def test_rejected_remote_never_reports_progress(self):
        player, ns, executed = self.make_player()
        reports = []
        flags = []
        advances = []

        player.playback_mode = "remote"
        player.identity_ready = True
        player.expected_duration = 1395.0
        player.validated = False
        player._duration = 30.0

        ns["duration_valid"] = lambda actual, expected: False
        ns["report_async"] = lambda *args, **kwargs: reports.append(args)
        ns["source_session"] = types.SimpleNamespace(
            flag=lambda reason: flags.append(reason),
            advance=lambda: (
                advances.append(True) or {"index": 1},
                {"url": "https://example.invalid/good.mkv"},
            ),
        )

        player.emit()

        self.assertFalse(player.validated)
        self.assertTrue(player.suppress_progress)
        self.assertTrue(player.rejection_started)
        self.assertTrue(player.stopped)
        self.assertEqual(reports, [])
        self.assertEqual(flags, ["bad_stream"])
        self.assertEqual(len(advances), 1)
        self.assertEqual(
            executed,
            [
                "PlayMedia("
                "plugin://plugin.video.apollomedia/"
                "?action=play_session_stream&index=1,"
                "noresume)"
            ],
        )

    def test_local_playback_reports_without_remote_validation(self):
        player, ns, _ = self.make_player()
        reports = []

        player.playback_mode = "local"
        player.identity_ready = True
        player.validated = True

        def forbidden_remote_validation(*args, **kwargs):
            raise AssertionError(
                "local playback must not enter remote validation"
            )

        player._validate_remote = forbidden_remote_validation
        ns["report_async"] = lambda *args, **kwargs: reports.append(args)

        player.emit()

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][-2:], (300.0, 1395.0))


if __name__ == "__main__":
    unittest.main()

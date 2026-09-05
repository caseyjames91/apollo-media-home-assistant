import ast
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def load_functions(*names):
    tree = ast.parse(MAIN.read_text(encoding="utf-8"), filename=str(MAIN))
    wanted = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    missing = set(names) - {n.name for n in wanted}
    if missing:
        raise AssertionError(f"missing functions in main.py: {sorted(missing)}")
    module = ast.Module(body=wanted, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {}
    exec(compile(module, str(MAIN), "exec"), ns)
    return ns


class FakeTag:
    def __init__(self):
        self.resume_calls = []
        self.playcount_calls = []
        self.duration_calls = []

    def setTitle(self, value): pass
    def setUniqueID(self, value, key): pass
    def setSeason(self, value): pass
    def setEpisode(self, value): pass
    def setTvShowTitle(self, value): pass
    def setPlaycount(self, value): self.playcount_calls.append(value)
    def setDuration(self, value): self.duration_calls.append(value)
    def setResumePoint(self, position, duration): self.resume_calls.append((position, duration))


class FakeListItem:
    def __init__(self, label=None, path=None):
        self.label = label
        self.path = path
        self.properties = {}
        self.tag = FakeTag()
        self.context = []

    def setProperty(self, key, value):
        self.properties[key] = value

    def getVideoInfoTag(self):
        return self.tag

    def addContextMenuItems(self, items, replaceItems=False):
        self.context.extend(items)


class FakeWindow:
    def __init__(self, window_id):
        self.window_id = window_id
        self.properties = {}

    def setProperty(self, key, value):
        self.properties[key] = value


class ResumeResolutionContractTests(unittest.TestCase):
    def test_browse_item_renders_canonical_ams_resume_state(self):
        ns = load_functions("playable_media")
        added = {}
        ns.update({
            "xbmcgui": types.SimpleNamespace(ListItem=FakeListItem),
            "xbmcplugin": types.SimpleNamespace(
                addDirectoryItem=lambda handle, target, item, is_folder: added.update(
                    handle=handle, target=target, item=item, is_folder=is_folder
                )
            ),
            "HANDLE": 7,
            "ADDON": object(),
            "ams": types.SimpleNamespace(progress_for=lambda *a, **k: (300.0, 1440.0, False)),
            "apply_common": lambda *a, **k: None,
            "_play_context": lambda *a, **k: [],
            "_remote_params": lambda *a, **k: {"imdb": "tt1"},
            "url": lambda action, **values: f"plugin://apollo/?action={action}",
        })

        ns["playable_media"]({"title": "Test", "imdb_id": "tt1"}, "movie")

        self.assertEqual(
            added["item"].tag.resume_calls,
            [(0.0, 0.0), (300.0, 1440.0)],
        )
        self.assertEqual(added["item"].tag.duration_calls, [1440])
        self.assertEqual(added["item"].properties["IsPlayable"], "true")

    def test_resolved_stream_does_not_reapply_ams_resume_point(self):
        ns = load_functions("_resolve_remote")
        resolved = {}

        def forbidden_resume(*args, **kwargs):
            raise AssertionError("_resolve_remote must not make a second AMS resume decision")

        ns.update({
            "xbmcgui": types.SimpleNamespace(ListItem=FakeListItem, Window=FakeWindow),
            "xbmcplugin": types.SimpleNamespace(
                setResolvedUrl=lambda handle, succeeded, item: resolved.update(
                    handle=handle, succeeded=succeeded, item=item
                )
            ),
            "HANDLE": 7,
            "ADDON": object(),
            "ams": types.SimpleNamespace(resume=forbidden_resume),
            "source_session": types.SimpleNamespace(
                load=lambda: {
                    "resume_mode": "fixed",
                    "resume_position": 300.0,
                }
            ),
        })

        stream = {
            "url": "https://example.invalid/video.mkv",
            "provider": "torrentio",
            "title": "Example Stream",
        }
        params = {"title": "Test", "imdb": "tt1", "season": "0", "episode": "0"}

        ns["_resolve_remote"](stream, params)

        self.assertTrue(resolved["succeeded"])
        self.assertEqual(resolved["item"].tag.resume_calls, [])
        self.assertEqual(resolved["item"].properties["StartOffset"], "300.0")
        self.assertEqual(resolved["item"].properties["IsPlayable"], "true")


if __name__ == "__main__":
    unittest.main()

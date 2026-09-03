#!/usr/bin/env python3
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "kodi" / "plugin.video.apollomedia"

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-kodi-package.py <package.zip>")

package = Path(sys.argv[1])
if not package.is_absolute():
    package = ROOT / package
if not package.is_file():
    raise SystemExit(f"ERROR: Kodi package not found: {package}")

def should_package(path: Path) -> bool:
    return (
        path.is_file()
        and "tests" not in path.parts
        and not path.name.startswith("PATCH_NOTES_")
        and not path.name.endswith(".pyc")
        and "__pycache__" not in path.parts
    )

expected = {
    str(Path("plugin.video.apollomedia") / p.relative_to(SRC)).replace("\\", "/"): p
    for p in SRC.rglob("*")
    if should_package(p)
}

with zipfile.ZipFile(package) as zf:
    actual = {name: zf.read(name) for name in zf.namelist() if not name.endswith("/")}

missing = sorted(set(expected) - set(actual))
extra = sorted(set(actual) - set(expected))
mismatched = sorted(
    name for name, src in expected.items()
    if name in actual and actual[name] != src.read_bytes()
)

if missing or extra or mismatched:
    if missing:
        print("Missing package files:", *missing, sep="\n  ")
    if extra:
        print("Unexpected package files:", *extra, sep="\n  ")
    if mismatched:
        print("Package/source byte mismatches:", *mismatched, sep="\n  ")
    raise SystemExit("ERROR: Kodi release package is not byte-identical to canonical addon source")

main_name = "plugin.video.apollomedia/main.py"
main_text = actual[main_name].decode("utf-8")
legacy = ["jellyfin_item_id", 'action="seasons"', "series_id="]
found = [token for token in legacy if token in main_text]
if found:
    raise SystemExit("ERROR: legacy media route contract found in packaged main.py: " + ", ".join(found))

required = [
    'folder("Library Movies", url("library_movies"))',
    'folder("Library Shows", url("library_shows"))',
    'folder("Continue Watching", url("continue"))',
    'def playable_media(',
    '"play_remote_command",',
    '"RunPlugin(" + remote_target + ")"',
    'def play_remote_command(',
    'def play_remote(',
    '"Play Locally"',
    '"Pick Stream Manually"',
]
absent = [token for token in required if token not in main_text]
if absent:
    raise SystemExit("ERROR: rebuilt canonical media/playback contract missing from packaged main.py: " + ", ".join(absent))

forbidden_root_actions = [
    'action_item("Current Stream Info"',
    'action_item("Try Next Stream"',
    'action_item("Flag Current Stream"',
    'action_item("Detect Device Compatibility"',
    'action_item("Link TorBox"',
    'action_item("Relink TorBox"',
]
home_text = main_text.split("def home():", 1)[1].split("\ndef ", 1)[0]
found_root = [token for token in forbidden_root_actions if token in home_text]
if found_root:
    raise SystemExit("ERROR: maintenance/playback actions leaked into rebuilt root: " + ", ".join(found_root))

print(f"PASS: Kodi package exactly matches canonical source: {package.name}")

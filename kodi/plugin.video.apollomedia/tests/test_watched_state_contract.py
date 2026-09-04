from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()
AMS = (ROOT / "resources/lib/ams.py").read_text()


def test_ams_client_has_explicit_watched_mutation():
    assert "def set_watched(addon, media_id, watched):" in AMS
    assert 'f"profiles/{pid}/media/{media_id}/watched"' in AMS
    assert 'payload={"watched": bool(watched)}' in AMS


def test_playable_items_replace_kodi_default_context_menu():
    assert "replaceItems=True" in MAIN


def test_apollo_context_menu_exposes_watched_controls():
    assert '"Apollo: Mark watched"' in MAIN
    assert '"Apollo: Mark unwatched"' in MAIN
    assert "url('set_watched'" in MAIN


def test_dispatch_routes_watched_state_to_ams():
    assert 'elif action == "set_watched":' in MAIN
    assert "ams.set_watched(ADDON, media_id, watched)" in MAIN
    assert 'xbmc.executebuiltin("Container.Refresh")' in MAIN

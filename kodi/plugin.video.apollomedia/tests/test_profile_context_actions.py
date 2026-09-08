from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()
AMS = (ROOT / "resources/lib/ams.py").read_text()


def test_favorites_are_first_class_profile_state():
    assert 'folder("Favorites", url("favorites"))' in MAIN
    assert 'def favorites():' in MAIN
    assert 'def set_favorite(p):' in MAIN
    assert 'def favorites(addon):' in AMS
    assert 'profiles/{pid}/favorites' in AMS


def test_clear_progress_is_conditional():
    assert 'def clear_progress(addon, media_id):' in AMS
    assert 'float(position or 0.0) > 0.0' in MAIN
    assert '"Apollo: Clear progress"' in MAIN


def test_episode_navigation_uses_canonical_series_identity():
    assert '"Apollo: Go to Series"' in MAIN
    assert '"Apollo: Go to Season"' in MAIN
    assert 'def series_identity(addon, imdb_id):' in AMS
    assert 'discovery/series-identity/{imdb_id}' in AMS
    assert 'Container.Update(' in MAIN


def test_hierarchy_watched_actions_exist():
    assert 'def watched_summary(addon):' in AMS
    assert 'def set_hierarchy_watched(addon, imdb_id, watched, season=None):' in AMS
    assert 'context=_season_context(imdb, season)' in MAIN
    assert 'context=_season_context(imdb, season_number)' in MAIN


def test_context_order_and_stream_scope():
    play = MAIN.index('# Logical order: playback -> episode navigation -> profile state -> stream tools.')
    nav = MAIN.index('actions.extend(_episode_navigation_context(row, season))', play)
    profile = MAIN.index('actions.extend(_watchlist_context(row, media_type))', nav)
    session = MAIN.index('if _source_session_matches_item(', profile)
    assert play < nav < profile < session
    assert '"Apollo: Current Stream Info"' in MAIN
    assert '"Apollo: Try Next Stream"' in MAIN
    assert '"Apollo: Flag Current Stream"' in MAIN


def test_show_folders_use_combined_context():
    assert 'def _show_context(row, watchlisted=None, favorite=None):' in MAIN
    assert 'context=_show_context(row)' in MAIN
    assert 'context=_show_context(row, watchlisted=True)' in MAIN
    assert 'context=_show_context(row, favorite=True)' in MAIN

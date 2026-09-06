from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_watchlist_is_profile_owned_persistent_state():
    model = (ROOT / "app/models/watchlist.py").read_text()

    assert 'ForeignKey("profiles.id", ondelete="CASCADE")' in model
    assert 'ForeignKey("media.id", ondelete="CASCADE")' in model
    assert '"uq_profile_media_watchlist"' in model
    assert "added_at:" in model


def test_watchlist_routes_are_exposed():
    api = (ROOT / "app/api/watchlist.py").read_text()
    main = (ROOT / "app/main.py").read_text()

    assert '@router.get("/profiles/{profile_id}/watchlist")' in api
    assert '"/profiles/{profile_id}/watchlist/{media_id}"' in api
    assert "@router.put(" in api
    assert "@router.delete(" in api
    assert "app.include_router(watchlist.router)" in main


def test_watchlist_membership_is_queryable_for_client_toggles():
    api = (ROOT / "app/api/watchlist.py").read_text()

    assert "get_profile_watchlist_membership" in api
    assert '"watchlisted": item is not None' in api


def test_watchlist_is_title_level_not_episode_level():
    service = (ROOT / "app/services/watchlist.py").read_text()

    assert 'WATCHLIST_MEDIA_TYPES = {"movie", "show"}' in service
    assert "media.media_type not in WATCHLIST_MEDIA_TYPES" in service


def test_watchlist_returns_canonical_presentation_metadata():
    service = (ROOT / "app/services/watchlist.py").read_text()

    for field in (
        '"canonical_id": media.canonical_id',
        '"title": media.title',
        '"poster_url": media.poster_url',
        '"backdrop_url": media.backdrop_url',
        '"available_locally": _available_locally(',
        '"watchlisted": True',
    ):
        assert field in service

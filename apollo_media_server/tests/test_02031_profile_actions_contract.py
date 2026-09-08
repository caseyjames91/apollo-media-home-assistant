from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "app/main.py").read_text()
PROGRESS = (ROOT / "app/api/progress.py").read_text()
FAVORITES_API = (ROOT / "app/api/favorites.py").read_text()
FAVORITES_SERVICE = (ROOT / "app/services/favorites.py").read_text()
FAVORITE_MODEL = (ROOT / "app/models/favorite.py").read_text()
MODELS_INIT = (ROOT / "app/models/__init__.py").read_text()


def test_clear_progress_endpoint_exists():
    assert '/media/{media_id}/clear-progress' in PROGRESS
    assert 'progress.position_seconds = 0.0' in PROGRESS
    assert 'progress.watched = False' in PROGRESS
    assert 'progress.watched_at = None' in PROGRESS


def test_hierarchy_watched_endpoints_exist():
    assert '/series/{imdb_id}/watched' in PROGRESS
    assert '/series/{imdb_id}/season/{season}/watched' in PROGRESS
    assert '_set_hierarchy_watched' in PROGRESS


def test_watched_summary_exists():
    assert '/profiles/{profile_id}/watched-summary' in PROGRESS
    assert '"series": series_out' in PROGRESS
    assert '"seasons": seasons_out' in PROGRESS


def test_favorites_are_profile_owned_canonical_membership():
    assert 'class FavoriteItem(Base):' in FAVORITE_MODEL
    assert '"profile_id"' in FAVORITE_MODEL
    assert '"media_id"' in FAVORITE_MODEL
    assert 'FAVORITE_MEDIA_TYPES = {"movie", "show"}' in FAVORITES_SERVICE
    assert '/profiles/{profile_id}/favorites' in FAVORITES_API


def test_favorites_router_and_model_are_registered():
    assert 'favorites' in MAIN
    assert 'app.include_router(favorites.router)' in MAIN
    assert 'FavoriteItem' in MODELS_INIT

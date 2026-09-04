from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_API = (ROOT / "app/api/progress.py").read_text()
PROGRESS_SCHEMA = (ROOT / "app/schemas/progress.py").read_text()


def test_explicit_watched_update_schema_exists():
    assert "class WatchedUpdate(BaseModel):" in PROGRESS_SCHEMA
    assert "watched: bool" in PROGRESS_SCHEMA


def test_profile_media_watched_endpoint_exists():
    assert '@router.put("/profiles/{profile_id}/media/{media_id}/watched")' in PROGRESS_API
    assert "payload: WatchedUpdate" in PROGRESS_API


def test_watched_mutation_sets_authoritative_state():
    assert "progress.watched = bool(payload.watched)" in PROGRESS_API
    assert "progress.watched_at = now if payload.watched else None" in PROGRESS_API
    assert "progress.updated_at = now" in PROGRESS_API


def test_watched_mutation_can_create_profile_progress_row():
    assert "if progress is None:" in PROGRESS_API
    assert "progress = Progress(" in PROGRESS_API
    assert "profile_id=profile_id" in PROGRESS_API
    assert "media_id=media_id" in PROGRESS_API

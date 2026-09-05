from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMDB = (ROOT / "app/services/tmdb.py").read_text()
PROGRESS = (ROOT / "app/api/progress.py").read_text()

def test_tmdb_movie_details_persist_canonical_runtime():
    assert 'runtime_seconds = _runtime_seconds(details.get("runtime"))' in TMDB
    assert 'media.runtime_seconds = runtime_seconds' in TMDB

def test_tmdb_episode_details_persist_canonical_runtime():
    assert 'runtime_seconds = _runtime_seconds(episode_details.get("runtime"))' in TMDB

def test_profile_duration_cannot_become_validation_authority():
    assert 'prior_duration' not in PROGRESS
    assert 'expected_duration = max(0, int(media.runtime_seconds or 0))' in PROGRESS

def test_missing_canonical_runtime_does_not_validate_against_profile_history():
    validator = PROGRESS.split('def _upsert_one(', 1)[1].split('@router.put("/progress")', 1)[0]
    assert 'if expected_duration > 0 and duration > 0:' in validator
    assert 'prior_duration' not in validator

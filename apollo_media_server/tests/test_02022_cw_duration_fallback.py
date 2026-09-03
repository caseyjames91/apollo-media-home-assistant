from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = (ROOT / "app/api/progress.py").read_text()

def test_cw_uses_accepted_profile_duration_when_runtime_not_backfilled():
    assert 'expected_duration = max(0, int(m.runtime_seconds or 0)) or max(0, int(duration or 0))' in PROGRESS
    assert 'expected_duration_seconds=expected_duration or None' in PROGRESS

def test_progress_guard_uses_existing_accepted_duration_when_runtime_not_backfilled():
    assert 'prior_duration = max(0, int(progress.duration_seconds or 0)) if progress is not None else 0' in PROGRESS
    assert 'expected_duration = max(0, int(media.runtime_seconds or 0)) or prior_duration' in PROGRESS
    assert 'ratio < 0.50 or ratio > 1.75' in PROGRESS

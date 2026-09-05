from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = (ROOT / "app/api/progress.py").read_text()

def test_cw_expected_runtime_uses_canonical_media_only():
    assert 'expected_duration = max(0, int(m.runtime_seconds or 0))' in PROGRESS
    assert 'expected_duration_seconds=expected_duration or None' in PROGRESS
    assert 'or max(0, int(duration or 0))' not in PROGRESS

def test_progress_guard_uses_canonical_media_runtime_only():
    assert 'expected_duration = max(0, int(media.runtime_seconds or 0))' in PROGRESS
    assert 'prior_duration' not in PROGRESS
    assert 'ratio < 0.50 or ratio > 1.75' in PROGRESS

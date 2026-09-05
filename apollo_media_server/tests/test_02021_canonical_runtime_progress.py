from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_media_owns_runtime():
    s=(ROOT/'app/models/media.py').read_text()
    assert 'runtime_seconds:' in s
def test_discovery_persists_runtime():
    s=(ROOT/'app/api/discovery.py').read_text()
    assert 'canonical.runtime_seconds = episode_runtime * 60' in s
def test_continue_watching_exposes_runtime():
    s=(ROOT/'app/api/progress.py').read_text()
    assert 'expected_duration = max(0, int(m.runtime_seconds or 0))' in s
    assert 'expected_duration_seconds=expected_duration or None' in s
def test_progress_rejects_implausible_provider_duration():
    s=(ROOT/'app/api/progress.py').read_text()
    assert 'ratio < 0.50 or ratio > 1.75' in s
    assert 'return progress, media, False' in s

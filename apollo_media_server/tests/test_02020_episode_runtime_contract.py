from pathlib import Path
def test_episode_runtime_fallback():
    s=(Path(__file__).resolve().parents[1]/"app/api/discovery.py").read_text()
    assert 'show_raw.get("episode_run_time")' in s
    assert 'episode_runtime = int(row.get("runtime") or show_runtime or 0)' in s
    assert '"expected_duration_seconds":episode_runtime*60' in s

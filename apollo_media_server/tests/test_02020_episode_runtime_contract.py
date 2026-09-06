from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_episode_runtime_fallback():
    discovery = (ROOT / "app/api/discovery.py").read_text()
    episodes = (ROOT / "app/services/episodes.py").read_text()

    assert 'show_raw.get("episode_run_time")' in discovery
    assert "materialize_season(" in discovery
    assert "show_runtime_minutes=show_runtime" in discovery

    assert 'raw.get("runtime") or show_runtime_minutes or 0' in episodes
    assert "canonical.runtime_seconds = runtime_minutes * 60" in episodes
    assert '"expected_duration_seconds": runtime_minutes * 60' in episodes

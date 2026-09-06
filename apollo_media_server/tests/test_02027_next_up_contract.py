from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_next_up_routes_are_exposed():
    api = (ROOT / "app/api/next_up.py").read_text()
    main = (ROOT / "app/main.py").read_text()

    assert '@router.get("/profiles/{profile_id}/next-up")' in api
    assert '"/profiles/{profile_id}/media/{media_id}/next-episode"' in api
    assert "app.include_router(next_up.router)" in main


def test_next_up_uses_shared_episode_materializer():
    service = (ROOT / "app/services/next_up.py").read_text()

    assert "from app.services.episodes import materialize_season" in service
    assert "materialize_season(" in service
    assert "season_number < current_season" in service


def test_next_up_excludes_specials_and_future_episodes():
    service = (ROOT / "app/services/next_up.py").read_text()

    assert "if number <= 0:" in service
    assert "_is_future_episode(" in service
    assert "date.fromisoformat(value) > date.today()" in service


def test_next_up_skips_completed_successors_but_keeps_partial_progress():
    service = (ROOT / "app/services/next_up.py").read_text()

    assert "if progress and progress.watched:" in service
    assert '"position_seconds": position' in service
    assert '"progress_fraction": (' in service


def test_continue_watching_owns_latest_unfinished_episode():
    service = (ROOT / "app/services/next_up.py").read_text()

    assert "if not progress.watched:" in service
    assert 'target["state"] = "next_up"' in service


def test_next_up_exposes_local_availability():
    service = (ROOT / "app/services/next_up.py").read_text()

    assert "available_locally: bool = False" in service
    assert '"available_locally": available_locally' in service
    assert 'item.get("available_locally")' in service


def test_next_episode_endpoint_does_not_own_playback_intent():
    api = (ROOT / "app/api/next_up.py").read_text()

    assert "next_episode_after(" in api
    assert "playback" not in api.lower()

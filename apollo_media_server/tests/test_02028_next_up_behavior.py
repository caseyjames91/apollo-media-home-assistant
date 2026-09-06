import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.services import next_up


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _episode(
    *,
    series_tmdb_id="100",
    season,
    episode,
    title=None,
    imdb_id="tt0100",
):
    return Media(
        media_type="episode",
        canonical_id=(
            f"tmdb:{series_tmdb_id}:s{season}e{episode}"
        ),
        imdb_id=imdb_id,
        tmdb_id=f"{series_tmdb_id}{season}{episode}",
        title=title or f"Episode {episode}",
        series_title="Test Show",
        season=season,
        episode=episode,
        runtime_seconds=2700,
    )


def _progress(
    profile_id,
    media_id,
    *,
    watched,
    position=0,
    duration=2700,
    updated_at=None,
):
    return Progress(
        profile_id=profile_id,
        media_id=media_id,
        position_seconds=position,
        duration_seconds=duration,
        watched=watched,
        watched_at=(
            updated_at
            if watched
            else None
        ),
        updated_at=(
            updated_at
            or datetime(2026, 9, 5, tzinfo=timezone.utc)
        ),
    )


def _install_fake_tmdb(monkeypatch):
    monkeypatch.setattr(
        next_up,
        "_integration",
        lambda db: SimpleNamespace(
            base_url="https://example.invalid",
            access_token="test",
        ),
    )

    async def fake_tmdb_json(integration, path, params=None):
        if path == "/tv/100":
            return {
                "id": 100,
                "name": "Test Show",
                "poster_path": "/poster.jpg",
                "backdrop_path": "/backdrop.jpg",
                "episode_run_time": [45],
                "external_ids": {
                    "imdb_id": "tt0100",
                },
                "seasons": [
                    {"season_number": 0},
                    {"season_number": 1},
                    {"season_number": 2},
                ],
            }

        if path == "/tv/100/season/1":
            return {
                "episodes": [
                    {
                        "id": 10011,
                        "episode_number": 1,
                        "name": "S1E1",
                        "air_date": "2026-01-01",
                        "runtime": 45,
                    },
                    {
                        "id": 10012,
                        "episode_number": 2,
                        "name": "S1E2",
                        "air_date": "2026-01-08",
                        "runtime": 45,
                    },
                ],
            }

        if path == "/tv/100/season/2":
            return {
                "episodes": [
                    {
                        "id": 10021,
                        "episode_number": 1,
                        "name": "S2E1",
                        "air_date": "2026-02-01",
                        "runtime": 45,
                    },
                    {
                        "id": 10022,
                        "episode_number": 2,
                        "name": "S2E2 Future",
                        "air_date": "2099-01-01",
                        "runtime": 45,
                    },
                ],
            }

        raise AssertionError(f"Unexpected TMDB path: {path}")

    monkeypatch.setattr(
        next_up,
        "_tmdb_json",
        fake_tmdb_json,
    )


def test_next_episode_crosses_season_and_skips_watched(
    monkeypatch,
):
    db = _db()
    _install_fake_tmdb(monkeypatch)

    profile = Profile(id=uuid.uuid4(), name="Casey")
    current = _episode(season=1, episode=1, title="S1E1")
    already_watched = _episode(
        season=1,
        episode=2,
        title="S1E2",
    )

    db.add_all([profile, current, already_watched])
    db.flush()

    db.add_all(
        [
            _progress(
                profile.id,
                current.id,
                watched=True,
                position=2700,
            ),
            _progress(
                profile.id,
                already_watched.id,
                watched=True,
                position=2700,
            ),
        ]
    )
    db.commit()

    result = asyncio.run(
        next_up.next_episode_after(
            db,
            profile.id,
            current,
        )
    )

    assert result is not None
    assert result["season"] == 2
    assert result["episode"] == 1
    assert result["canonical_id"] == "tmdb:100:s2e1"
    assert result["watched"] is False
    assert result["position_seconds"] == 0


def test_next_episode_preserves_target_partial_progress_per_profile(
    monkeypatch,
):
    db = _db()
    _install_fake_tmdb(monkeypatch)

    profile_a = Profile(id=uuid.uuid4(), name="Profile A")
    profile_b = Profile(id=uuid.uuid4(), name="Profile B")
    current = _episode(season=1, episode=1, title="S1E1")
    target = _episode(season=1, episode=2, title="S1E2")

    db.add_all(
        [
            profile_a,
            profile_b,
            current,
            target,
        ]
    )
    db.flush()

    db.add_all(
        [
            _progress(
                profile_a.id,
                current.id,
                watched=True,
                position=2700,
            ),
            _progress(
                profile_a.id,
                target.id,
                watched=False,
                position=600,
            ),
            _progress(
                profile_b.id,
                target.id,
                watched=True,
                position=2700,
            ),
        ]
    )
    db.commit()

    result = asyncio.run(
        next_up.next_episode_after(
            db,
            profile_a.id,
            current,
        )
    )

    assert result is not None
    assert result["season"] == 1
    assert result["episode"] == 2
    assert result["position_seconds"] == 600
    assert result["duration_seconds"] == 2700
    assert result["progress_fraction"] == 600 / 2700
    assert result["watched"] is False


def test_profile_next_up_omits_show_owned_by_continue_watching(
    monkeypatch,
):
    db = _db()
    _install_fake_tmdb(monkeypatch)

    profile = Profile(id=uuid.uuid4(), name="Casey")
    current = _episode(season=1, episode=1, title="S1E1")

    db.add_all([profile, current])
    db.flush()

    db.add(
        _progress(
            profile.id,
            current.id,
            watched=False,
            position=900,
        )
    )
    db.commit()

    result = asyncio.run(
        next_up.profile_next_up(
            db,
            profile.id,
        )
    )

    assert result == []


def test_profile_next_up_advances_completed_show(
    monkeypatch,
):
    db = _db()
    _install_fake_tmdb(monkeypatch)

    profile = Profile(id=uuid.uuid4(), name="Casey")
    current = _episode(season=1, episode=1, title="S1E1")

    db.add_all([profile, current])
    db.flush()

    db.add(
        _progress(
            profile.id,
            current.id,
            watched=True,
            position=2700,
        )
    )
    db.commit()

    result = asyncio.run(
        next_up.profile_next_up(
            db,
            profile.id,
        )
    )

    assert len(result) == 1
    assert result[0]["state"] == "next_up"
    assert result[0]["season"] == 1
    assert result[0]["episode"] == 2


def test_next_episode_does_not_offer_future_episode(
    monkeypatch,
):
    db = _db()
    _install_fake_tmdb(monkeypatch)

    profile = Profile(id=uuid.uuid4(), name="Casey")
    current = _episode(season=2, episode=1, title="S2E1")

    db.add_all([profile, current])
    db.flush()

    db.add(
        _progress(
            profile.id,
            current.id,
            watched=True,
            position=2700,
        )
    )
    db.commit()

    result = asyncio.run(
        next_up.next_episode_after(
            db,
            profile.id,
            current,
        )
    )

    assert result is None

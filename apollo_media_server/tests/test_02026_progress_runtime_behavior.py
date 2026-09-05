import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.progress import _upsert_one
from app.db.base import Base
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.schemas.progress import ProgressUpsert


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _payload(profile_id, *, position, duration, updated_at):
    return ProgressUpsert(
        profile_id=profile_id,
        media_type="movie",
        canonical_id="tt0453562",
        imdb_id="tt0453562",
        tmdb_id="109410",
        title="42",
        position_seconds=position,
        duration_seconds=duration,
        updated_at=updated_at,
    )


def test_poisoned_profile_duration_cannot_lock_correct_playback():
    db = _db()
    profile = Profile(id=uuid.uuid4(), name="Test")
    media = Media(
        media_type="movie",
        canonical_id="tt0453562",
        imdb_id="tt0453562",
        tmdb_id="109410",
        title="42",
        runtime_seconds=None,
    )
    db.add_all([profile, media])
    db.flush()

    old = datetime(2026, 9, 1, tzinfo=timezone.utc)
    progress = Progress(
        profile_id=profile.id,
        media_id=media.id,
        position_seconds=957.208,
        duration_seconds=1086.185,
        updated_at=old,
    )
    db.add(progress)
    db.commit()

    incoming = old + timedelta(days=4)
    result, result_media, changed = _upsert_one(
        db,
        _payload(
            profile.id,
            position=2265.0,
            duration=7695.7,
            updated_at=incoming,
        ),
        profile.id,
    )

    assert changed is True
    assert result_media.id == media.id
    assert result.position_seconds == 2265.0
    assert result.duration_seconds == 7695.7
    assert result.updated_at == incoming


def test_canonical_runtime_still_rejects_wrong_duration():
    db = _db()
    profile = Profile(id=uuid.uuid4(), name="Test")
    media = Media(
        media_type="movie",
        canonical_id="tt0453562",
        imdb_id="tt0453562",
        tmdb_id="109410",
        title="42",
        runtime_seconds=7680,
    )
    db.add_all([profile, media])
    db.commit()

    result, result_media, changed = _upsert_one(
        db,
        _payload(
            profile.id,
            position=100.0,
            duration=1086.185,
            updated_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
        ),
        profile.id,
    )

    assert changed is False
    assert result is None
    assert result_media.id == media.id

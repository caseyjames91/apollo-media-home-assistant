import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.models.profile import Profile
from app.models.watchlist import WatchlistItem
from app.services.watchlist import (
    add_to_watchlist,
    get_watchlist_item,
    list_watchlist,
    remove_from_watchlist,
)


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _media(
    media_type,
    canonical_id,
    title,
):
    return Media(
        media_type=media_type,
        canonical_id=canonical_id,
        title=title,
        tmdb_id=canonical_id.split(":")[-1],
        poster_url=f"https://img/{title}/poster.jpg",
        backdrop_url=f"https://img/{title}/backdrop.jpg",
    )


def test_same_title_is_independent_per_profile():
    db = _db()

    profile_a = Profile(
        id=uuid.uuid4(),
        name="Profile A",
    )
    profile_b = Profile(
        id=uuid.uuid4(),
        name="Profile B",
    )
    movie = _media(
        "movie",
        "tmdb:100",
        "Test Movie",
    )

    db.add_all([profile_a, profile_b, movie])
    db.commit()

    add_to_watchlist(
        db,
        profile_a.id,
        movie,
    )

    assert get_watchlist_item(
        db,
        profile_a.id,
        movie.id,
    ) is not None
    assert get_watchlist_item(
        db,
        profile_b.id,
        movie.id,
    ) is None


def test_add_is_idempotent_and_remove_is_idempotent():
    db = _db()

    profile = Profile(
        id=uuid.uuid4(),
        name="Casey",
    )
    show = _media(
        "show",
        "tmdb:200",
        "Test Show",
    )

    db.add_all([profile, show])
    db.commit()

    first = add_to_watchlist(
        db,
        profile.id,
        show,
    )
    second = add_to_watchlist(
        db,
        profile.id,
        show,
    )

    rows = list(
        db.scalars(
            select(WatchlistItem).where(
                WatchlistItem.profile_id == profile.id,
                WatchlistItem.media_id == show.id,
            )
        )
    )

    assert len(rows) == 1
    assert first["media_id"] == second["media_id"]

    assert remove_from_watchlist(
        db,
        profile.id,
        show.id,
    ) is True
    assert remove_from_watchlist(
        db,
        profile.id,
        show.id,
    ) is False


def test_episode_cannot_be_added_to_title_watchlist():
    db = _db()

    profile = Profile(
        id=uuid.uuid4(),
        name="Casey",
    )
    episode = Media(
        media_type="episode",
        canonical_id="tmdb:300:s1e1",
        title="Pilot",
        series_title="Test Show",
        season=1,
        episode=1,
    )

    db.add_all([profile, episode])
    db.commit()

    with pytest.raises(
        ValueError,
        match="movie and show",
    ):
        add_to_watchlist(
            db,
            profile.id,
            episode,
        )


def test_list_returns_metadata_local_state_and_newest_first():
    db = _db()

    profile = Profile(
        id=uuid.uuid4(),
        name="Casey",
    )
    movie = _media(
        "movie",
        "tmdb:400",
        "Movie",
    )
    show = _media(
        "show",
        "tmdb:500",
        "Show",
    )

    db.add_all([profile, movie, show])
    db.commit()

    add_to_watchlist(
        db,
        profile.id,
        movie,
    )
    add_to_watchlist(
        db,
        profile.id,
        show,
    )

    db.add(
        LocalAvailability(
            media_id=show.id,
            provider="sonarr",
            provider_item_id="500",
            source_path="/tv/Show",
            kodi_path="smb://media/Show",
            available=True,
        )
    )
    db.commit()

    rows = list_watchlist(
        db,
        profile.id,
    )

    assert [row["title"] for row in rows] == [
        "Show",
        "Movie",
    ]
    assert rows[0]["available_locally"] is True
    assert rows[1]["available_locally"] is False
    assert rows[0]["watchlisted"] is True

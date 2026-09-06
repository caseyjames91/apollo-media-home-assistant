from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.models.watchlist import WatchlistItem


WATCHLIST_MEDIA_TYPES = {"movie", "show"}


def _available_locally(
    db: Session,
    media_id: uuid.UUID,
) -> bool:
    return (
        db.scalar(
            select(LocalAvailability.id)
            .where(
                LocalAvailability.media_id == media_id,
                LocalAvailability.available.is_(True),
            )
            .limit(1)
        )
        is not None
    )


def _dto(
    db: Session,
    item: WatchlistItem,
    media: Media,
) -> dict:
    return {
        "media_id": str(media.id),
        "media_type": media.media_type,
        "canonical_id": media.canonical_id,
        "imdb_id": media.imdb_id,
        "tmdb_id": media.tmdb_id,
        "tvdb_id": media.tvdb_id,
        "title": media.title,
        "series_title": media.series_title,
        "year": media.year,
        "overview": media.overview,
        "poster_url": media.poster_url,
        "backdrop_url": media.backdrop_url,
        "runtime_seconds": int(media.runtime_seconds or 0),
        "available_locally": _available_locally(
            db,
            media.id,
        ),
        "watchlisted": True,
        "added_at": item.added_at,
    }


def get_watchlist_item(
    db: Session,
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
) -> WatchlistItem | None:
    return db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.profile_id == profile_id,
            WatchlistItem.media_id == media_id,
        )
    )


def list_watchlist(
    db: Session,
    profile_id: uuid.UUID,
) -> list[dict]:
    rows = db.execute(
        select(WatchlistItem, Media)
        .join(Media, Media.id == WatchlistItem.media_id)
        .where(WatchlistItem.profile_id == profile_id)
        .order_by(WatchlistItem.added_at.desc())
    ).all()

    return [
        _dto(db, item, media)
        for item, media in rows
    ]


def add_to_watchlist(
    db: Session,
    profile_id: uuid.UUID,
    media: Media,
) -> dict:
    if media.media_type not in WATCHLIST_MEDIA_TYPES:
        raise ValueError(
            "Watchlist supports movie and show media only"
        )

    item = get_watchlist_item(
        db,
        profile_id,
        media.id,
    )
    if item is None:
        item = WatchlistItem(
            profile_id=profile_id,
            media_id=media.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    return _dto(db, item, media)


def remove_from_watchlist(
    db: Session,
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
) -> bool:
    item = get_watchlist_item(
        db,
        profile_id,
        media_id,
    )
    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True

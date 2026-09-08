from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.favorite import FavoriteItem
from app.models.local_availability import LocalAvailability
from app.models.media import Media


FAVORITE_MEDIA_TYPES = {"movie", "show"}


def _available_locally(db: Session, media_id: uuid.UUID) -> bool:
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


def _dto(db: Session, item: FavoriteItem, media: Media) -> dict:
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
        "available_locally": _available_locally(db, media.id),
        "favorite": True,
        "added_at": item.added_at,
    }


def get_favorite_item(
    db: Session,
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
) -> FavoriteItem | None:
    return db.scalar(
        select(FavoriteItem).where(
            FavoriteItem.profile_id == profile_id,
            FavoriteItem.media_id == media_id,
        )
    )


def list_favorites(db: Session, profile_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(FavoriteItem, Media)
        .join(Media, Media.id == FavoriteItem.media_id)
        .where(FavoriteItem.profile_id == profile_id)
        .order_by(FavoriteItem.added_at.desc())
    ).all()
    return [_dto(db, item, media) for item, media in rows]


def add_favorite(
    db: Session,
    profile_id: uuid.UUID,
    media: Media,
) -> dict:
    if media.media_type not in FAVORITE_MEDIA_TYPES:
        raise ValueError("Favorites supports movie and show media only")

    item = get_favorite_item(db, profile_id, media.id)
    if item is None:
        item = FavoriteItem(profile_id=profile_id, media_id=media.id)
        db.add(item)
        db.commit()
        db.refresh(item)

    return _dto(db, item, media)


def remove_favorite(
    db: Session,
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
) -> bool:
    item = get_favorite_item(db, profile_id, media_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.schemas.media import MediaCreate


router = APIRouter(prefix="/media", tags=["media"])


def _locals(db, media_id):
    return list(
        db.scalars(
            select(LocalAvailability)
            .where(LocalAvailability.media_id == media_id)
            .order_by(LocalAvailability.provider, LocalAvailability.provider_item_id)
        )
    )


def _local_source_dto(row: LocalAvailability) -> dict:
    return {
        "provider": row.provider,
        "provider_item_id": row.provider_item_id,
        "available": row.available,
        # A path is authoritative only while Arr says the file is present.
        "source_path": (row.source_path or None) if row.available else None,
        "quality": row.quality if row.available else None,
        "updated_at": row.updated_at,
    }


def _dto(db, row):
    local_sources = _locals(db, row.id)
    available_sources = [source for source in local_sources if source.available]
    playback_source = next(
        (source for source in available_sources if source.kodi_path),
        None,
    )
    return {
        "id": row.id,
        "media_type": row.media_type,
        "canonical_id": row.canonical_id,
        "title": row.title,
        "series_title": row.series_title,
        "imdb_id": row.imdb_id,
        "tmdb_id": row.tmdb_id,
        "tvdb_id": row.tvdb_id,
        "year": row.year,
        "season": row.season,
        "episode": row.episode,
        "overview": row.overview,
        "poster_url": row.poster_url,
        "backdrop_url": row.backdrop_url,
        "available_locally": bool(available_sources),
        # Arr owns availability + filesystem source location. Kodi routing is
        # separate and can remain unset until the playback transport is chosen.
        "local_playback_path": (
            playback_source.kodi_path or None
            if playback_source is not None
            else None
        ),
        "local_sources": [_local_source_dto(source) for source in local_sources],
    }


@router.post("", status_code=201)
def upsert_media(payload: MediaCreate, db: Session = Depends(get_db)):
    q = select(Media).where(Media.media_type == payload.media_type, Media.canonical_id == payload.canonical_id)
    q = q.where(Media.season.is_(None) if payload.season is None else Media.season == payload.season)
    q = q.where(Media.episode.is_(None) if payload.episode is None else Media.episode == payload.episode)
    row = db.scalar(q)
    if row is None:
        row = Media(**payload.model_dump())
        db.add(row)
    else:
        for key, value in payload.model_dump().items():
            if value is not None:
                setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _dto(db, row)


@router.get("")
def list_media(
    media_type: str | None = None,
    available_locally: bool | None = None,
    db: Session = Depends(get_db),
):
    q = select(Media).order_by(Media.title)
    if media_type:
        q = q.where(Media.media_type == media_type)
    rows = list(db.scalars(q))
    result = [_dto(db, row) for row in rows]
    if available_locally is not None:
        result = [row for row in result if row["available_locally"] is available_locally]
    return result


@router.get("/{media_id}")
def get_media(media_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Media, media_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return _dto(db, row)

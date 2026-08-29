import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.schemas.media import MediaCreate

router = APIRouter(prefix="/media", tags=["media"])


def _local(db, media_id):
    return db.scalar(select(LocalAvailability).where(LocalAvailability.media_id == media_id, LocalAvailability.available.is_(True)))


def _dto(db, row):
    local = _local(db, row.id)
    return {"id": row.id, "media_type": row.media_type, "canonical_id": row.canonical_id, "title": row.title,
            "series_title": row.series_title, "imdb_id": row.imdb_id, "tmdb_id": row.tmdb_id, "tvdb_id": row.tvdb_id,
            "year": row.year, "season": row.season, "episode": row.episode, "overview": row.overview,
            "poster_url": row.poster_url, "backdrop_url": row.backdrop_url,
            "available_locally": bool(local and local.kodi_path), "local_playback_path": local.kodi_path if local else None}


@router.post("", status_code=201)
def upsert_media(payload: MediaCreate, db: Session = Depends(get_db)):
    q = select(Media).where(Media.media_type == payload.media_type, Media.canonical_id == payload.canonical_id)
    q = q.where(Media.season.is_(None) if payload.season is None else Media.season == payload.season)
    q = q.where(Media.episode.is_(None) if payload.episode is None else Media.episode == payload.episode)
    row = db.scalar(q)
    if row is None:
        row = Media(**payload.model_dump()); db.add(row)
    else:
        for k,v in payload.model_dump().items():
            if v is not None: setattr(row,k,v)
    db.commit(); db.refresh(row)
    return _dto(db,row)


@router.get("")
def list_media(media_type: str | None = None, available_locally: bool | None = None, db: Session = Depends(get_db)):
    q = select(Media).order_by(Media.title)
    if media_type: q = q.where(Media.media_type == media_type)
    rows = list(db.scalars(q))
    result = [_dto(db,r) for r in rows]
    if available_locally is not None: result = [r for r in result if r["available_locally"] is available_locally]
    return result


@router.get("/{media_id}")
def get_media(media_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Media, media_id)
    if row is None: raise HTTPException(status_code=404, detail="Media not found")
    return _dto(db,row)

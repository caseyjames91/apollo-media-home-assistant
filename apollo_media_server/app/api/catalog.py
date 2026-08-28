import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.media import Media
from app.models.profile import Profile

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
def catalog(media_type: str | None = None, limit: int = 500, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 2000)
    q = select(Media).where(Media.media_type.in_(["movie", "show"])).order_by(Media.title)
    if media_type:
        q = q.where(Media.media_type == media_type)
    rows = list(db.scalars(q.limit(limit)))
    return [{
        "media_id": str(m.id),
        "media_type": m.media_type,
        "canonical_id": m.canonical_id,
        "imdb_id": m.imdb_id,
        "tmdb_id": m.tmdb_id,
        "jellyfin_item_id": m.jellyfin_item_id,
        "title": m.title,
    } for m in rows]


@router.get("/profiles/{profile_id}/catalog")
def profile_catalog(profile_id: uuid.UUID, media_type: str | None = None, limit: int = 500, db: Session = Depends(get_db)):
    if db.get(Profile, profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return catalog(media_type=media_type, limit=limit, db=db)

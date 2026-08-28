from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.schemas.progress import ContinueWatchingItem, ProgressUpsert

router = APIRouter(tags=["progress"])

@router.put("/progress")
def upsert_progress(payload: ProgressUpsert, db: Session = Depends(get_db)):
    if db.get(Profile, payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    q = select(Media).where(
        Media.media_type == payload.media_type,
        Media.canonical_id == payload.canonical_id,
    )
    q = q.where(Media.season.is_(None) if payload.season is None else Media.season == payload.season)
    q = q.where(Media.episode.is_(None) if payload.episode is None else Media.episode == payload.episode)
    media = db.scalar(q)

    if media is None:
        media = Media(
            media_type=payload.media_type,
            canonical_id=payload.canonical_id,
            imdb_id=payload.imdb_id,
            tmdb_id=payload.tmdb_id,
            jellyfin_item_id=payload.jellyfin_item_id,
            title=payload.title,
            season=payload.season,
            episode=payload.episode,
        )
        db.add(media)
        db.flush()
    else:
        media.title = payload.title
        media.imdb_id = payload.imdb_id or media.imdb_id
        media.tmdb_id = payload.tmdb_id or media.tmdb_id
        media.jellyfin_item_id = payload.jellyfin_item_id or media.jellyfin_item_id

    progress = db.scalar(select(Progress).where(
        Progress.profile_id == payload.profile_id,
        Progress.media_id == media.id,
    ))
    if progress is None:
        progress = Progress(profile_id=payload.profile_id, media_id=media.id)
        db.add(progress)

    progress.position_seconds = max(0, payload.position_seconds)
    progress.duration_seconds = max(0, payload.duration_seconds)
    progress.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "media_id": str(media.id)}

@router.get("/profiles/{profile_id}/continue-watching", response_model=list[ContinueWatchingItem])
def continue_watching(profile_id: uuid.UUID, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    rows = db.execute(
        select(Progress, Media)
        .join(Media, Media.id == Progress.media_id)
        .where(Progress.profile_id == profile.id)
        .order_by(Progress.updated_at.desc())
    ).all()

    result = []
    for p, m in rows:
        duration = max(0.0, p.duration_seconds)
        fraction = p.position_seconds / duration if duration > 0 else 0.0
        if p.position_seconds <= 0 or fraction >= 0.90:
            continue
        result.append(ContinueWatchingItem(
            media_id=m.id,
            media_type=m.media_type,
            canonical_id=m.canonical_id,
            title=m.title,
            season=m.season,
            episode=m.episode,
            position_seconds=p.position_seconds,
            duration_seconds=duration,
            progress_fraction=fraction,
            updated_at=p.updated_at,
        ))
    return result

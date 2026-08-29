from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.schemas.progress import ContinueWatchingItem, ProgressImport, ProgressUpsert

router = APIRouter(tags=["progress"])


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _media_type(value: str, season: int | None, episode: int | None) -> str:
    raw = str(value or "movie").strip().lower()
    if raw in {"series", "episode", "tv"} and (int(season or 0) > 0 or int(episode or 0) > 0):
        return "episode"
    if raw in {"series", "show", "tv"}:
        return "show"
    return "movie" if raw == "movie" else raw


def _upsert_one(db: Session, payload, profile_id: uuid.UUID) -> tuple[Progress, Media, bool]:
    media_type = _media_type(payload.media_type, payload.season, payload.episode)
    season = payload.season if media_type == "episode" else None
    episode = payload.episode if media_type == "episode" else None
    canonical_id = str(payload.canonical_id or payload.imdb_id or payload.tmdb_id or payload.jellyfin_item_id or "").strip()
    if not canonical_id:
        raise HTTPException(status_code=422, detail="Progress item has no canonical identity")

    q = select(Media).where(Media.media_type == media_type, Media.canonical_id == canonical_id)
    q = q.where(Media.season.is_(None) if season is None else Media.season == season)
    q = q.where(Media.episode.is_(None) if episode is None else Media.episode == episode)
    media = db.scalar(q)

    if media is None:
        media = Media(
            media_type=media_type,
            canonical_id=canonical_id,
            imdb_id=payload.imdb_id,
            tmdb_id=payload.tmdb_id,
            jellyfin_item_id=payload.jellyfin_item_id,
            title=payload.title,
            season=season,
            episode=episode,
        )
        db.add(media)
        db.flush()
    else:
        media.title = payload.title or media.title
        media.imdb_id = payload.imdb_id or media.imdb_id
        media.tmdb_id = payload.tmdb_id or media.tmdb_id
        media.jellyfin_item_id = payload.jellyfin_item_id or media.jellyfin_item_id

    progress = db.scalar(select(Progress).where(
        Progress.profile_id == profile_id,
        Progress.media_id == media.id,
    ))
    incoming_updated = _utc(payload.updated_at)
    if progress is None:
        progress = Progress(profile_id=profile_id, media_id=media.id)
        db.add(progress)
    else:
        existing_updated = _utc(progress.updated_at)
        if incoming_updated < existing_updated:
            return progress, media, False

    progress.position_seconds = max(0, payload.position_seconds)
    progress.duration_seconds = max(0, payload.duration_seconds)
    progress.updated_at = incoming_updated
    return progress, media, True


@router.put("/progress")
def upsert_progress(payload: ProgressUpsert, db: Session = Depends(get_db)):
    if db.get(Profile, payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    progress, media, changed = _upsert_one(db, payload, payload.profile_id)
    db.commit()
    return {"status": "ok", "media_id": str(media.id), "changed": changed}


@router.post("/progress/import")
def import_progress(payload: ProgressImport, db: Session = Depends(get_db)):
    if db.get(Profile, payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    changed = 0
    skipped = 0
    for item in payload.items:
        _, _, did_change = _upsert_one(db, item, payload.profile_id)
        if did_change:
            changed += 1
        else:
            skipped += 1
    db.commit()
    return {"status": "ok", "changed": changed, "skipped_older": skipped, "received": len(payload.items)}


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
        series = None
        if m.media_type == "episode":
            series = db.scalar(select(Media).where(
                Media.media_type == "show",
                Media.canonical_id == m.canonical_id,
            ))
        result.append(ContinueWatchingItem(
            media_id=m.id,
            media_type=m.media_type,
            canonical_id=m.canonical_id,
            title=m.title,
            series_title=series.title if series else None,
            imdb_id=m.imdb_id or (series.imdb_id if series else None),
            tmdb_id=m.tmdb_id or (series.tmdb_id if series else None),
            jellyfin_item_id=m.jellyfin_item_id,
            artwork_jellyfin_item_id=(series.jellyfin_item_id if series else m.jellyfin_item_id),
            season=m.season,
            episode=m.episode,
            position_seconds=p.position_seconds,
            duration_seconds=duration,
            progress_fraction=fraction,
            updated_at=p.updated_at,
        ))
    return result

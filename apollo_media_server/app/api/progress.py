from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.schemas.progress import ContinueWatchingItem, ProgressImport, ProgressUpsert

router = APIRouter(tags=["progress"])


def _utc(value):
    if value is None: return datetime.now(timezone.utc)
    if value.tzinfo is None: return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _media_type(value, season, episode):
    raw = str(value or "movie").lower()
    if raw in {"series","show","episode","tv"} and (season is not None or episode is not None): return "episode"
    if raw in {"series","show","tv"}: return "show"
    return "movie" if raw == "movie" else raw


def _upsert_one(db, payload, profile_id):
    media_type = _media_type(payload.media_type, payload.season, payload.episode)
    season = payload.season if media_type == "episode" else None
    episode = payload.episode if media_type == "episode" else None
    canonical_id = str(payload.canonical_id or payload.imdb_id or payload.tmdb_id or payload.tvdb_id or "").strip()
    if not canonical_id: raise HTTPException(status_code=422, detail="Progress item has no canonical identity")
    q = select(Media).where(Media.media_type == media_type, Media.canonical_id == canonical_id)
    q = q.where(Media.season.is_(None) if season is None else Media.season == season)
    q = q.where(Media.episode.is_(None) if episode is None else Media.episode == episode)
    media = db.scalar(q)
    if media is None:
        media = Media(
            media_type=media_type,
            canonical_id=canonical_id,
            title=payload.title,
            series_title=payload.series_title,
            imdb_id=payload.imdb_id,
            tmdb_id=payload.tmdb_id,
            tvdb_id=payload.tvdb_id,
            year=getattr(payload, "year", None),
            overview=getattr(payload, "overview", None),
            poster_url=getattr(payload, "poster_url", None),
            backdrop_url=getattr(payload, "backdrop_url", None),
            season=season,
            episode=episode,
        )
        db.add(media); db.flush()
    else:
        for field in (
            "title", "series_title", "imdb_id", "tmdb_id", "tvdb_id",
            "year", "overview", "poster_url", "backdrop_url",
        ):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(media, field, value)
    progress = db.scalar(select(Progress).where(Progress.profile_id == profile_id, Progress.media_id == media.id))
    incoming = _utc(payload.updated_at)
    if progress is None:
        progress = Progress(profile_id=profile_id, media_id=media.id); db.add(progress)
    elif incoming < _utc(progress.updated_at):
        return progress, media, False
    position, duration = max(0,payload.position_seconds), max(0,payload.duration_seconds)
    fraction = position / duration if duration > 0 else 0
    progress.position_seconds, progress.duration_seconds, progress.updated_at = position, duration, incoming
    if fraction >= .90:
        progress.watched = True
        progress.watched_at = progress.watched_at or incoming
    elif position > 0:
        progress.watched = False; progress.watched_at = None
    return progress, media, True


@router.put("/progress")
def upsert_progress(payload: ProgressUpsert, db: Session = Depends(get_db)):
    if db.get(Profile,payload.profile_id) is None: raise HTTPException(status_code=404, detail="Profile not found")
    p,m,changed=_upsert_one(db,payload,payload.profile_id); db.commit()
    return {"status":"ok","media_id":str(m.id),"changed":changed,"watched":p.watched}


@router.post("/progress/import")
def import_progress(payload: ProgressImport, db: Session = Depends(get_db)):
    if db.get(Profile,payload.profile_id) is None: raise HTTPException(status_code=404, detail="Profile not found")
    changed=skipped=0
    for item in payload.items:
        _,_,did=_upsert_one(db,item,payload.profile_id); changed += int(did); skipped += int(not did)
    db.commit(); return {"status":"ok","changed":changed,"skipped_older":skipped,"received":len(payload.items)}


@router.get("/profiles/{profile_id}/continue-watching", response_model=list[ContinueWatchingItem])
def continue_watching(profile_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(Profile,profile_id) is None: raise HTTPException(status_code=404, detail="Profile not found")
    rows=db.execute(select(Progress,Media).join(Media,Media.id==Progress.media_id).where(Progress.profile_id==profile_id).order_by(Progress.updated_at.desc())).all()
    out=[]
    for p,m in rows:
        duration=max(0,p.duration_seconds); fraction=p.position_seconds/duration if duration else 0
        if p.position_seconds <= 0 or p.watched or fraction >= .90: continue
        local=db.scalar(select(LocalAvailability).where(LocalAvailability.media_id==m.id,LocalAvailability.available.is_(True)))
        out.append(ContinueWatchingItem(
            media_id=m.id,
            media_type=m.media_type,
            canonical_id=m.canonical_id,
            title=m.title,
            series_title=m.series_title,
            imdb_id=m.imdb_id,
            tmdb_id=m.tmdb_id,
            tvdb_id=m.tvdb_id,
            year=m.year,
            overview=m.overview,
            poster_url=m.poster_url,
            backdrop_url=m.backdrop_url,
            season=m.season,
            episode=m.episode,
            position_seconds=p.position_seconds,
            duration_seconds=duration,
            progress_fraction=fraction,
            available_locally=bool(local and local.kodi_path),local_playback_path=local.kodi_path if local else None,updated_at=p.updated_at))
    return out

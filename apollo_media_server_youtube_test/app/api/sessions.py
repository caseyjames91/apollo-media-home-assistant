import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.media import Media
from app.models.playback_session import PlaybackSession
from app.models.profile import Profile
from app.schemas.session import PlaybackSessionRead, PlaybackSessionStart, PlaybackSessionUpdate

router = APIRouter(prefix="/playback-sessions", tags=["playback"])


@router.post("", response_model=PlaybackSessionRead, status_code=201)
def start_session(payload: PlaybackSessionStart, db: Session = Depends(get_db)):
    if db.get(Profile, payload.profile_id) is None: raise HTTPException(status_code=404, detail="Profile not found")
    if db.get(Media, payload.media_id) is None: raise HTTPException(status_code=404, detail="Media not found")
    row = PlaybackSession(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row


@router.patch("/{session_id}", response_model=PlaybackSessionRead)
def update_session(session_id: uuid.UUID, payload: PlaybackSessionUpdate, db: Session = Depends(get_db)):
    row = db.get(PlaybackSession, session_id)
    if row is None: raise HTTPException(status_code=404, detail="Playback session not found")
    if payload.state is not None: row.state = payload.state
    if payload.position_seconds is not None: row.position_seconds = max(0, payload.position_seconds)
    if payload.duration_seconds is not None: row.duration_seconds = max(0, payload.duration_seconds)
    row.updated_at = datetime.now(timezone.utc)
    if payload.ended:
        row.ended_at = row.updated_at; row.state = "ended"
    db.commit(); db.refresh(row); return row


@router.get("/active", response_model=list[PlaybackSessionRead])
def active_sessions(db: Session = Depends(get_db)):
    return list(db.scalars(select(PlaybackSession).where(PlaybackSession.ended_at.is_(None)).order_by(PlaybackSession.updated_at.desc())))

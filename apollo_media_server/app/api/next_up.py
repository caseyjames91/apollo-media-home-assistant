from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.media import Media
from app.models.profile import Profile
from app.services.next_up import next_episode_after, profile_next_up


router = APIRouter(tags=["next-up"])


def _profile(db: Session, profile_id: uuid.UUID) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )
    return profile


@router.get("/profiles/{profile_id}/next-up")
async def get_profile_next_up(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)
    return await profile_next_up(db, profile_id)


@router.get(
    "/profiles/{profile_id}/media/{media_id}/next-episode"
)
async def get_next_episode(
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)

    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(
            status_code=404,
            detail="Media not found",
        )
    if media.media_type != "episode":
        raise HTTPException(
            status_code=400,
            detail="Next episode requires episode media",
        )

    result = await next_episode_after(
        db,
        profile_id,
        media,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No next episode available",
        )

    return result

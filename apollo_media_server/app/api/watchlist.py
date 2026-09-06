from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.media import Media
from app.models.profile import Profile
from app.services.watchlist import (
    add_to_watchlist,
    get_watchlist_item,
    list_watchlist,
    remove_from_watchlist,
)


router = APIRouter(tags=["watchlist"])


def _profile(
    db: Session,
    profile_id: uuid.UUID,
) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )
    return profile


def _media(
    db: Session,
    media_id: uuid.UUID,
) -> Media:
    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(
            status_code=404,
            detail="Media not found",
        )
    return media


@router.get("/profiles/{profile_id}/watchlist")
def get_profile_watchlist(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)
    return list_watchlist(
        db,
        profile_id,
    )


@router.get(
    "/profiles/{profile_id}/watchlist/{media_id}"
)
def get_profile_watchlist_membership(
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)
    _media(db, media_id)

    item = get_watchlist_item(
        db,
        profile_id,
        media_id,
    )

    return {
        "media_id": str(media_id),
        "watchlisted": item is not None,
        "added_at": (
            item.added_at
            if item is not None
            else None
        ),
    }


@router.put(
    "/profiles/{profile_id}/watchlist/{media_id}"
)
def put_profile_watchlist_item(
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)
    media = _media(db, media_id)

    try:
        return add_to_watchlist(
            db,
            profile_id,
            media,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.delete(
    "/profiles/{profile_id}/watchlist/{media_id}",
    status_code=204,
)
def delete_profile_watchlist_item(
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    _profile(db, profile_id)
    _media(db, media_id)

    remove_from_watchlist(
        db,
        profile_id,
        media_id,
    )
    return Response(status_code=204)

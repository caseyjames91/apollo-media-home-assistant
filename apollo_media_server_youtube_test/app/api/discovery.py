from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.integration import Integration
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.services.tmdb import DEFAULT_BASE_URL, IMAGE_BASE_URL, TMDB_KIND, _headers

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _integration(db: Session) -> Integration:
    integration = db.scalar(
        select(Integration).where(
            Integration.kind == TMDB_KIND,
            Integration.enabled.is_(True),
        )
    )
    if integration is None or not integration.access_token:
        raise HTTPException(status_code=503, detail="TMDB is not configured")
    return integration


def _base(integration: Integration) -> str:
    return (integration.base_url or DEFAULT_BASE_URL).rstrip("/")


def _image(path) -> str | None:
    value = str(path or "").strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return IMAGE_BASE_URL + (value if value.startswith("/") else "/" + value)


def _year(value) -> int | None:
    value = str(value or "")
    return int(value[:4]) if len(value) >= 4 and value[:4].isdigit() else None


def _existing(db: Session, media_type: str, tmdb_id: str) -> Media | None:
    # Identity reconciliation is deliberately ID based, never title based.
    return db.scalar(
        select(Media).where(
            Media.media_type == media_type,
            or_(
                Media.tmdb_id == tmdb_id,
                Media.canonical_id == f"tmdb:{tmdb_id}",
            ),
        ).limit(1)
    )


def _local(db: Session, media: Media | None) -> bool:
    if media is None:
        return False
    return db.scalar(
        select(LocalAvailability.id).where(
            LocalAvailability.media_id == media.id,
            LocalAvailability.available.is_(True),
        ).limit(1)
    ) is not None


def _reconcile(db: Session, media_type: str, raw: dict) -> dict:
    tmdb_id = str(raw.get("id") or "").strip()
    if not tmdb_id:
        raise ValueError("TMDB result has no id")

    title = str(
        raw.get("title") if media_type == "movie" else raw.get("name")
        or raw.get("original_name")
        or "Unknown"
    )
    release = raw.get("release_date") if media_type == "movie" else raw.get("first_air_date")

    media = _existing(db, media_type, tmdb_id)
    if media is None:
        media = Media(
            media_type=media_type,
            canonical_id=f"tmdb:{tmdb_id}",
            tmdb_id=tmdb_id,
            title=title,
            year=_year(release),
            overview=raw.get("overview"),
            poster_url=_image(raw.get("poster_path")),
            backdrop_url=_image(raw.get("backdrop_path")),
        )
        db.add(media)
        db.flush()
    else:
        # TMDB owns presentation metadata. Keep the existing Apollo row/UUID.
        media.tmdb_id = tmdb_id
        media.title = title or media.title
        media.year = _year(release) or media.year
        media.overview = raw.get("overview") or media.overview
        media.poster_url = _image(raw.get("poster_path")) or media.poster_url
        media.backdrop_url = _image(raw.get("backdrop_path")) or media.backdrop_url

    return {
        "media_id": str(media.id),
        "media_type": media.media_type,
        "canonical_id": media.canonical_id,
        "imdb_id": media.imdb_id,
        "tmdb_id": media.tmdb_id,
        "title": media.title,
        "year": media.year,
        "overview": media.overview,
        "poster_url": media.poster_url,
        "backdrop_url": media.backdrop_url,
        "available_locally": _local(db, media),
    }


async def _request(db: Session, path: str, media_type: str, params: dict | None = None) -> list[dict]:
    integration = _integration(db)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(
            f"{_base(integration)}{path}",
            headers=_headers(integration),
            params=params or {},
        )
        response.raise_for_status()
        raw = response.json() or {}

    out = []
    for item in raw.get("results") or []:
        try:
            out.append(_reconcile(db, media_type, item))
        except (TypeError, ValueError):
            continue
    db.commit()
    return out


@router.get("/popular/{media_type}")
async def popular(media_type: str, db: Session = Depends(get_db)):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(db, f"/{tmdb_kind}/popular", kind)


@router.get("/trending/{media_type}")
async def trending(media_type: str, db: Session = Depends(get_db)):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(db, f"/trending/{tmdb_kind}/week", kind)


@router.get("/search/{media_type}")
async def search_media(
    media_type: str,
    q: str = Query(min_length=1, max_length=200),
    db: Session = Depends(get_db),
):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(
        db,
        f"/search/{tmdb_kind}",
        kind,
        {"query": q, "include_adult": "false"},
    )


def _kind(value: str) -> str:
    value = str(value or "").strip().lower()
    if value in {"movie", "movies"}:
        return "movie"
    if value in {"show", "shows", "tv"}:
        return "show"
    raise HTTPException(status_code=422, detail="media_type must be movie or show")

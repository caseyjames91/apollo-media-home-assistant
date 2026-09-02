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
async def popular(media_type: str, page: int = Query(default=1, ge=1, le=500), db: Session = Depends(get_db)):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(db, f"/{tmdb_kind}/popular", kind, {"page": page})


@router.get("/trending/{media_type}")
async def trending(media_type: str, page: int = Query(default=1, ge=1, le=500), db: Session = Depends(get_db)):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(db, f"/trending/{tmdb_kind}/week", kind, {"page": page})


def _show_payload(db: Session, tmdb_id: str, raw: dict) -> dict:
    media = _existing(db, "show", tmdb_id)
    external = raw.get("external_ids") or {}
    imdb_id = str(external.get("imdb_id") or "").strip() or None
    if media is None:
        media = Media(
            media_type="show", canonical_id=f"tmdb:{tmdb_id}", tmdb_id=tmdb_id,
            imdb_id=imdb_id,
            title=str(raw.get("name") or raw.get("original_name") or "Unknown"),
            year=_year(raw.get("first_air_date")), overview=raw.get("overview"),
            poster_url=_image(raw.get("poster_path")),
            backdrop_url=_image(raw.get("backdrop_path")),
        )
        db.add(media); db.flush()
    else:
        if imdb_id: media.imdb_id = imdb_id
        media.title = str(raw.get("name") or media.title or "Unknown")
        media.year = _year(raw.get("first_air_date")) or media.year
        media.overview = raw.get("overview") or media.overview
        media.poster_url = _image(raw.get("poster_path")) or media.poster_url
        media.backdrop_url = _image(raw.get("backdrop_path")) or media.backdrop_url
    return {
        "media_id": str(media.id), "media_type": "show",
        "canonical_id": media.canonical_id, "imdb_id": media.imdb_id,
        "tmdb_id": media.tmdb_id, "title": media.title, "year": media.year,
        "overview": media.overview, "poster_url": media.poster_url,
        "backdrop_url": media.backdrop_url,
        "available_locally": _local(db, media),
    }

async def _tmdb_json(integration: Integration, path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(
            f"{_base(integration)}{path}", headers=_headers(integration), params=params or {}
        )
        response.raise_for_status()
        return response.json() or {}

@router.get("/series-identity/{imdb_id}")
def series_identity(imdb_id: str, db: Session = Depends(get_db)):
    target = str(imdb_id or "").strip()
    media = db.scalar(
        select(Media).where(
            Media.media_type == "show",
            Media.imdb_id == target,
        ).limit(1)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Series identity not found")
    return {
        "media_id": str(media.id),
        "media_type": "show",
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


@router.get("/show/{tmdb_id}")
async def show_details(tmdb_id: str, db: Session = Depends(get_db)):
    integration = _integration(db)
    raw = await _tmdb_json(integration, f"/tv/{tmdb_id}", {"append_to_response": "external_ids"})
    result = _show_payload(db, str(tmdb_id), raw)
    result["seasons"] = [{
        "season": int(row.get("season_number") or 0),
        "title": str(row.get("name") or ("Specials" if int(row.get("season_number") or 0) == 0 else f"Season {int(row.get('season_number') or 0)}")),
        "overview": row.get("overview"), "poster_url": _image(row.get("poster_path")),
        "air_date": row.get("air_date"), "episode_count": int(row.get("episode_count") or 0),
    } for row in (raw.get("seasons") or [])]
    db.commit()
    return result

@router.get("/show/{tmdb_id}/season/{season_number}")
async def show_season(tmdb_id: str, season_number: int, db: Session = Depends(get_db)):
    integration = _integration(db)
    show_raw = await _tmdb_json(integration, f"/tv/{tmdb_id}", {"append_to_response": "external_ids"})
    show = _show_payload(db, str(tmdb_id), show_raw)
    raw = await _tmdb_json(integration, f"/tv/{tmdb_id}/season/{int(season_number)}")
    show_runtime = next(
        (int(value) for value in (show_raw.get("episode_run_time") or []) if int(value or 0) > 0),
        0,
    )
    episodes=[]
    for row in raw.get("episodes") or []:
        number=int(row.get("episode_number") or 0)
        if number <= 0: continue
        canonical_id=f"tmdb:{tmdb_id}:s{int(season_number)}e{number}"
        episode_runtime = int(row.get("runtime") or show_runtime or 0)
        episode_row={
            "media_type":"episode", "canonical_id":canonical_id,
            "imdb_id":show.get("imdb_id"), "tmdb_id":str(row.get("id") or ""),
            "series_tmdb_id":str(tmdb_id), "series_title":show.get("title"),
            "title":str(row.get("name") or f"Episode {number}"),
            "season":int(season_number), "episode":number,
            "overview":row.get("overview"),
            "poster_url":_image(row.get("still_path")) or show.get("poster_url"),
            "backdrop_url":show.get("backdrop_url"), "air_date":row.get("air_date"),
            "runtime":episode_runtime,
            "expected_duration_seconds":episode_runtime*60,
            "available_locally":False,
        }
        canonical=db.scalar(select(Media).where(
            Media.media_type=="episode", Media.canonical_id==canonical_id,
            Media.season==int(season_number), Media.episode==number
        ))
        if canonical is None:
            canonical=Media(
                media_type="episode", canonical_id=canonical_id,
                imdb_id=episode_row["imdb_id"], tmdb_id=episode_row["tmdb_id"],
                title=episode_row["title"], series_title=episode_row["series_title"],
                overview=episode_row["overview"], poster_url=episode_row["poster_url"],
                backdrop_url=episode_row["backdrop_url"],
                season=int(season_number), episode=number,
            )
            db.add(canonical); db.flush()
        else:
            canonical.imdb_id=episode_row["imdb_id"] or canonical.imdb_id
            canonical.tmdb_id=episode_row["tmdb_id"] or canonical.tmdb_id
            canonical.title=episode_row["title"] or canonical.title
            canonical.series_title=episode_row["series_title"] or canonical.series_title
            canonical.overview=episode_row["overview"] or canonical.overview
            canonical.poster_url=episode_row["poster_url"] or canonical.poster_url
            canonical.backdrop_url=episode_row["backdrop_url"] or canonical.backdrop_url
        episode_row["media_id"]=str(canonical.id)
        episodes.append(episode_row)
    if show.get("imdb_id"):
        local_rows=db.scalars(select(Media).where(
            Media.media_type=="episode", Media.imdb_id==show.get("imdb_id"),
            Media.season==int(season_number)
        )).all()
        local_by_episode={int(row.episode or 0):row for row in local_rows}
        for episode in episodes:
            local=local_by_episode.get(int(episode["episode"]))
            if local is None: continue
            episode.update({
                "imdb_id":local.imdb_id or show.get("imdb_id"),
                "title":local.title or episode["title"],
                "overview":local.overview or episode["overview"],
                "poster_url":local.poster_url or episode["poster_url"],
                "backdrop_url":local.backdrop_url or episode["backdrop_url"],
                "available_locally":_local(db, local),
            })
    db.commit()
    return {"show":show, "season":int(season_number),
            "title":str(raw.get("name") or f"Season {int(season_number)}"),
            "episodes":episodes}

@router.get("/search/{media_type}")
async def search_media(
    media_type: str,
    q: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1, le=500),
    db: Session = Depends(get_db),
):
    kind = _kind(media_type)
    tmdb_kind = "movie" if kind == "movie" else "tv"
    return await _request(
        db,
        f"/search/{tmdb_kind}",
        kind,
        {"query": q, "include_adult": "false", "page": page},
    )


def _kind(value: str) -> str:
    value = str(value or "").strip().lower()
    if value in {"movie", "movies"}:
        return "movie"
    if value in {"show", "shows", "tv"}:
        return "show"
    raise HTTPException(status_code=422, detail="media_type must be movie or show")

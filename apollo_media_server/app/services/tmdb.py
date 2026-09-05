from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.models.media import Media


TMDB_KIND = "tmdb"
DEFAULT_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"


def _headers(integration: Integration) -> dict[str, str]:
    if not integration.access_token:
        raise ValueError("TMDB integration has no read access token")
    return {
        "Authorization": f"Bearer {integration.access_token}",
        "Accept": "application/json",
    }


def _base_url(integration: Integration) -> str:
    return (integration.base_url or DEFAULT_BASE_URL).rstrip("/")


def _image_url(path: str | None) -> str | None:
    path = str(path or "").strip()
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return IMAGE_BASE_URL + path


async def resolve_external_ids(db: Session, media: Media) -> Media:
    """Lazily complete provider-facing external IDs and persist them."""
    if media.imdb_id:
        return media

    tmdb_id = str(media.tmdb_id or "").strip()
    if not tmdb_id:
        return media

    media_type = str(media.media_type or "").strip().lower()
    if media_type not in {"movie", "show"}:
        return media

    integration = db.scalar(
        select(Integration).where(
            Integration.kind == TMDB_KIND,
            Integration.enabled.is_(True),
        )
    )
    if integration is None or not integration.access_token:
        raise RuntimeError("TMDB is not configured")

    tmdb_kind = "movie" if media_type == "movie" else "tv"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(
            f"{_base_url(integration)}/{tmdb_kind}/{tmdb_id}/external_ids",
            headers=_headers(integration),
        )
        response.raise_for_status()
        ids = response.json() or {}

    imdb_id = str(ids.get("imdb_id") or "").strip()
    if imdb_id:
        media.imdb_id = imdb_id
        db.commit()
        db.refresh(media)
    return media


async def test_integration(integration: Integration) -> dict:
    if integration.kind != TMDB_KIND:
        raise ValueError(f"Unsupported integration kind: {integration.kind}")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(
            f"{_base_url(integration)}/configuration",
            headers=_headers(integration),
        )
        response.raise_for_status()

    return {
        "kind": integration.kind,
        "name": integration.name,
        "ok": True,
        "server_name": "TMDB",
        "version": "v3",
    }


async def _find_by_imdb(client: httpx.AsyncClient, integration: Integration, imdb_id: str) -> dict:
    response = await client.get(
        f"{_base_url(integration)}/find/{imdb_id}",
        headers=_headers(integration),
        params={"external_source": "imdb_id"},
    )
    response.raise_for_status()
    return response.json() or {}


async def _movie_details(client: httpx.AsyncClient, integration: Integration, tmdb_id: str) -> dict:
    response = await client.get(
        f"{_base_url(integration)}/movie/{tmdb_id}",
        headers=_headers(integration),
    )
    response.raise_for_status()
    return response.json() or {}


async def _tv_details(client: httpx.AsyncClient, integration: Integration, tmdb_id: str) -> dict:
    response = await client.get(
        f"{_base_url(integration)}/tv/{tmdb_id}",
        headers=_headers(integration),
    )
    response.raise_for_status()
    return response.json() or {}


async def _episode_details(
    client: httpx.AsyncClient,
    integration: Integration,
    tmdb_series_id: str,
    season: int,
    episode: int,
) -> dict:
    response = await client.get(
        f"{_base_url(integration)}/tv/{tmdb_series_id}/season/{season}/episode/{episode}",
        headers=_headers(integration),
    )
    response.raise_for_status()
    return response.json() or {}


def _year(value) -> int | None:
    value = str(value or "").strip()
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def _runtime_seconds(value) -> int | None:
    try:
        minutes = int(value or 0)
    except (TypeError, ValueError):
        return None
    return minutes * 60 if minutes > 0 else None


def _apply_movie(media: Media, details: dict) -> None:
    media.tmdb_id = str(details.get("id") or media.tmdb_id or "") or None
    media.year = _year(details.get("release_date")) or media.year
    media.overview = details.get("overview") or media.overview
    runtime_seconds = _runtime_seconds(details.get("runtime"))
    if runtime_seconds is not None:
        media.runtime_seconds = runtime_seconds
    media.poster_url = _image_url(details.get("poster_path")) or media.poster_url
    media.backdrop_url = _image_url(details.get("backdrop_path")) or media.backdrop_url


def _apply_show(media: Media, details: dict) -> None:
    media.tmdb_id = str(details.get("id") or media.tmdb_id or "") or None
    media.year = _year(details.get("first_air_date")) or media.year
    media.overview = details.get("overview") or media.overview
    media.poster_url = _image_url(details.get("poster_path")) or media.poster_url
    media.backdrop_url = _image_url(details.get("backdrop_path")) or media.backdrop_url


async def sync_metadata(db: Session) -> dict:
    integration = db.scalar(
        select(Integration).where(
            Integration.kind == TMDB_KIND,
            Integration.enabled.is_(True),
        )
    )
    if integration is None or not integration.access_token:
        raise RuntimeError("TMDB is not configured")

    rows = list(db.scalars(select(Media).order_by(Media.title)))

    enriched = 0
    skipped = 0
    failed = 0

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # Cache series metadata because many episode rows share one show identity.
        show_cache: dict[str, dict] = {}

        for media in rows:
            try:
                media_type = str(media.media_type or "").lower()

                if media_type == "movie":
                    tmdb_id = str(media.tmdb_id or "").strip()

                    if not tmdb_id and media.imdb_id:
                        found = await _find_by_imdb(client, integration, media.imdb_id)
                        candidates = found.get("movie_results") or []
                        if candidates:
                            tmdb_id = str(candidates[0].get("id") or "")

                    if not tmdb_id:
                        skipped += 1
                        continue

                    details = await _movie_details(client, integration, tmdb_id)
                    _apply_movie(media, details)
                    enriched += 1
                    continue

                if media_type == "show":
                    tmdb_id = str(media.tmdb_id or "").strip()

                    if not tmdb_id and media.imdb_id:
                        found = await _find_by_imdb(client, integration, media.imdb_id)
                        candidates = found.get("tv_results") or []
                        if candidates:
                            tmdb_id = str(candidates[0].get("id") or "")

                    if not tmdb_id:
                        skipped += 1
                        continue

                    details = show_cache.get(tmdb_id)
                    if details is None:
                        details = await _tv_details(client, integration, tmdb_id)
                        show_cache[tmdb_id] = details

                    _apply_show(media, details)
                    enriched += 1
                    continue

                if media_type == "episode":
                    # Episode rows often carry the parent-series IMDb/TMDB identity
                    # in Apollo today. Resolve the series first, then the episode.
                    tmdb_series_id = str(media.tmdb_id or "").strip()

                    if media.imdb_id:
                        found = await _find_by_imdb(client, integration, media.imdb_id)
                        candidates = found.get("tv_results") or []
                        if candidates:
                            tmdb_series_id = str(candidates[0].get("id") or tmdb_series_id)

                    if not tmdb_series_id or media.season is None or media.episode is None:
                        skipped += 1
                        continue

                    show_details = show_cache.get(tmdb_series_id)
                    if show_details is None:
                        show_details = await _tv_details(client, integration, tmdb_series_id)
                        show_cache[tmdb_series_id] = show_details

                    episode_details = await _episode_details(
                        client,
                        integration,
                        tmdb_series_id,
                        int(media.season),
                        int(media.episode),
                    )

                    media.series_title = show_details.get("name") or media.series_title
                    media.year = (
                        _year(episode_details.get("air_date"))
                        or _year(show_details.get("first_air_date"))
                        or media.year
                    )
                    media.overview = episode_details.get("overview") or media.overview
                    runtime_seconds = _runtime_seconds(episode_details.get("runtime"))
                    if runtime_seconds is not None:
                        media.runtime_seconds = runtime_seconds

                    # Continue Watching should visually represent the series.
                    media.poster_url = (
                        _image_url(show_details.get("poster_path"))
                        or media.poster_url
                    )
                    media.backdrop_url = (
                        _image_url(show_details.get("backdrop_path"))
                        or media.backdrop_url
                    )

                    enriched += 1
                    continue

                skipped += 1

            except Exception:
                failed += 1

    db.commit()

    return {
        "status": "ok",
        "received": len(rows),
        "enriched": enriched,
        "skipped": skipped,
        "failed": failed,
    }

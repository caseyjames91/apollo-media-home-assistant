from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.models.local_availability import LocalAvailability
from app.models.media import Media


SUPPORTED_KINDS = {"radarr", "sonarr"}


def _headers(integration: Integration) -> dict[str, str]:
    if not integration.access_token:
        raise ValueError(f"{integration.kind} integration has no API key")
    return {"X-Api-Key": integration.access_token}


def _base_url(integration: Integration) -> str:
    return integration.base_url.rstrip("/")


async def test_integration(integration: Integration) -> dict:
    if integration.kind not in SUPPORTED_KINDS:
        raise ValueError(f"Unsupported integration kind: {integration.kind}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{_base_url(integration)}/api/v3/system/status",
            headers=_headers(integration),
        )
        response.raise_for_status()
        data = response.json()

    return {
        "kind": integration.kind,
        "name": integration.name,
        "ok": True,
        "server_name": data.get("appName") or data.get("instanceName"),
        "version": data.get("version"),
    }


def _norm(value) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value.lower() if value else None


def _quality(file_row: dict | None) -> str | None:
    if not file_row:
        return None
    quality = file_row.get("quality") or {}
    quality = quality.get("quality") or {}
    return quality.get("name")


def _join_path(root: str | None, file_row: dict | None) -> str:
    if not file_row:
        return root or ""
    path = file_row.get("path")
    if path:
        return path
    relative = file_row.get("relativePath")
    if not relative:
        return root or ""
    if not root:
        return relative
    return str(PurePosixPath(root.replace("\\", "/")) / relative.replace("\\", "/"))


def _upsert_local(
    db: Session,
    *,
    media: Media,
    provider: str,
    provider_item_id: str,
    source_path: str,
    available: bool,
    quality: str | None,
) -> LocalAvailability:
    query = select(LocalAvailability).where(
        LocalAvailability.media_id == media.id,
        LocalAvailability.provider == provider,
        LocalAvailability.provider_item_id == provider_item_id,
    )
    row = db.scalar(query)
    now = datetime.now(timezone.utc)

    if row is None:
        row = LocalAvailability(
            media_id=media.id,
            provider=provider,
            provider_item_id=provider_item_id,
            source_path=source_path or "",
            kodi_path="",
            available=available,
            quality=quality,
            updated_at=now,
        )
        db.add(row)
    else:
        row.source_path = source_path or ""
        # Local availability and Kodi playback routing are separate concerns.
        # Do not manufacture a Kodi path from an Arr filesystem path.
        row.available = available
        row.quality = quality
        row.updated_at = now

    return row


def _mark_provider_stale(db: Session, provider: str, seen_ids: set[tuple]) -> int:
    changed = 0
    rows = list(db.scalars(select(LocalAvailability).where(LocalAvailability.provider == provider)))
    for row in rows:
        identity = (row.media_id, row.provider_item_id)
        if identity not in seen_ids and row.available:
            row.available = False
            row.updated_at = datetime.now(timezone.utc)
            changed += 1
    return changed


def _match_radarr_movie(media: Media, radarr_by_tmdb: dict, radarr_by_imdb: dict) -> dict | None:
    if media.tmdb_id and _norm(media.tmdb_id) in radarr_by_tmdb:
        return radarr_by_tmdb[_norm(media.tmdb_id)]
    if media.imdb_id and _norm(media.imdb_id) in radarr_by_imdb:
        return radarr_by_imdb[_norm(media.imdb_id)]
    return None


async def sync_radarr(db: Session, integration: Integration) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{_base_url(integration)}/api/v3/movie",
            headers=_headers(integration),
        )
        response.raise_for_status()
        movies = response.json()

    by_tmdb = {_norm(m.get("tmdbId")): m for m in movies if _norm(m.get("tmdbId"))}
    by_imdb = {_norm(m.get("imdbId")): m for m in movies if _norm(m.get("imdbId"))}

    seen: set[tuple] = set()
    matched = 0
    available = 0

    media_rows = list(db.scalars(select(Media).where(Media.media_type == "movie")))
    for media in media_rows:
        arr = _match_radarr_movie(media, by_tmdb, by_imdb)
        if not arr:
            continue

        matched += 1
        file_row = arr.get("movieFile") if arr.get("hasFile") else None
        is_available = bool(arr.get("hasFile") and file_row)
        provider_item_id = str(arr.get("id"))
        source_path = _join_path(arr.get("path"), file_row)
        row = _upsert_local(
            db,
            media=media,
            provider="radarr",
            provider_item_id=provider_item_id,
            source_path=source_path,
            available=is_available,
            quality=_quality(file_row),
        )
        seen.add((media.id, provider_item_id))
        if row.available:
            available += 1

    stale = _mark_provider_stale(db, "radarr", seen)
    db.commit()
    return {
        "provider": "radarr",
        "matched": matched,
        "available": available,
        "marked_unavailable": stale,
    }


def _series_indexes(series_rows: list[dict]) -> tuple[dict, dict, dict]:
    by_tvdb = {}
    by_imdb = {}
    by_title_year = {}
    for series in series_rows:
        tvdb = _norm(series.get("tvdbId"))
        imdb = _norm(series.get("imdbId"))
        title = _norm(series.get("title"))
        year = series.get("year")
        if tvdb:
            by_tvdb[tvdb] = series
        if imdb:
            by_imdb[imdb] = series
        if title:
            by_title_year[(title, year)] = series
            by_title_year.setdefault((title, None), series)
    return by_tvdb, by_imdb, by_title_year


def _match_sonarr_series(
    media: Media,
    by_tvdb: dict,
    by_imdb: dict,
    by_title_year: dict,
) -> dict | None:
    if media.tvdb_id and _norm(media.tvdb_id) in by_tvdb:
        return by_tvdb[_norm(media.tvdb_id)]
    if media.imdb_id and _norm(media.imdb_id) in by_imdb:
        return by_imdb[_norm(media.imdb_id)]

    title = media.series_title if media.media_type == "episode" else media.title
    if title:
        key = (_norm(title), media.year)
        if key in by_title_year:
            return by_title_year[key]
        return by_title_year.get((_norm(title), None))
    return None


async def sync_sonarr(db: Session, integration: Integration) -> dict:
    headers = _headers(integration)
    base = _base_url(integration)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(f"{base}/api/v3/series", headers=headers)
        response.raise_for_status()
        series_rows = response.json()

        by_tvdb, by_imdb, by_title_year = _series_indexes(series_rows)

        media_rows = list(db.scalars(select(Media).where(Media.media_type.in_(["show", "series", "tvshow", "episode"]))))
        grouped: dict[int, list[Media]] = defaultdict(list)

        for media in media_rows:
            series = _match_sonarr_series(media, by_tvdb, by_imdb, by_title_year)
            if series and series.get("id") is not None:
                grouped[int(series["id"])].append(media)

        seen: set[tuple] = set()
        matched = 0
        available = 0

        for series_id, medias in grouped.items():
            series = next(s for s in series_rows if int(s.get("id")) == series_id)

            episodes_resp = await client.get(
                f"{base}/api/v3/episode",
                params={"seriesId": series_id},
                headers=headers,
            )
            episodes_resp.raise_for_status()
            episodes = episodes_resp.json()

            files_resp = await client.get(
                f"{base}/api/v3/episodefile",
                params={"seriesId": series_id},
                headers=headers,
            )
            files_resp.raise_for_status()
            episode_files = {int(f["id"]): f for f in files_resp.json() if f.get("id") is not None}

            episode_index = {
                (int(e.get("seasonNumber", -1)), int(e.get("episodeNumber", -1))): e
                for e in episodes
            }

            for media in medias:
                if media.media_type == "episode":
                    if media.season is None or media.episode is None:
                        continue
                    episode = episode_index.get((int(media.season), int(media.episode)))
                    if not episode:
                        continue

                    matched += 1
                    file_id = episode.get("episodeFileId")
                    file_row = episode_files.get(int(file_id)) if file_id else None
                    is_available = bool(episode.get("hasFile") and file_row)
                    provider_item_id = str(episode.get("id"))
                    source_path = _join_path(series.get("path"), file_row)
                    row = _upsert_local(
                        db,
                        media=media,
                        provider="sonarr",
                        provider_item_id=provider_item_id,
                        source_path=source_path,
                        available=is_available,
                        quality=_quality(file_row),
                    )
                else:
                    matched += 1
                    stats = series.get("statistics") or {}
                    is_available = bool(stats.get("episodeFileCount", 0))
                    provider_item_id = f"series:{series_id}"
                    row = _upsert_local(
                        db,
                        media=media,
                        provider="sonarr",
                        provider_item_id=provider_item_id,
                        source_path=series.get("path") or "",
                        available=is_available,
                        quality=None,
                    )

                seen.add((media.id, provider_item_id))
                if row.available:
                    available += 1

    stale = _mark_provider_stale(db, "sonarr", seen)
    db.commit()
    return {
        "provider": "sonarr",
        "matched": matched,
        "available": available,
        "marked_unavailable": stale,
    }


async def sync_local_availability(db: Session) -> dict:
    integrations = list(
        db.scalars(
            select(Integration).where(
                Integration.kind.in_(SUPPORTED_KINDS),
                Integration.enabled.is_(True),
            )
        )
    )

    results = []
    for integration in integrations:
        if integration.kind == "radarr":
            results.append(await sync_radarr(db, integration))
        elif integration.kind == "sonarr":
            results.append(await sync_sonarr(db, integration))

    return {
        "status": "ok",
        "integrations": len(integrations),
        "results": results,
    }

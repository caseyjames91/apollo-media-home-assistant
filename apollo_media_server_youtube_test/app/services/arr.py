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
        return ""
    path = file_row.get("path")
    if path:
        return path
    relative = file_row.get("relativePath")
    if not relative:
        return ""
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
        # Arr owns availability + source location only. Kodi playback routing
        # remains a separate concern and must not be manufactured here.
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
            row.source_path = ""
            row.quality = None
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
        source_path = _join_path(arr.get("path"), file_row) if is_available else ""
        row = _upsert_local(
            db,
            media=media,
            provider="radarr",
            provider_item_id=provider_item_id,
            source_path=source_path,
            available=is_available,
            quality=_quality(file_row) if is_available else None,
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
    by_tmdb = {}
    by_imdb = {}
    for series in series_rows:
        tvdb = _norm(series.get("tvdbId"))
        tmdb = _norm(series.get("tmdbId"))
        imdb = _norm(series.get("imdbId"))
        if tvdb:
            by_tvdb[tvdb] = series
        if tmdb:
            by_tmdb[tmdb] = series
        if imdb:
            by_imdb[imdb] = series
    return by_tvdb, by_tmdb, by_imdb


def _match_sonarr_series(
    media: Media,
    by_tvdb: dict,
    by_tmdb: dict,
    by_imdb: dict,
) -> dict | None:
    # Strict identity matching only. Sonarr is not a metadata authority and
    # title/year fallbacks can create false local-availability matches.
    if media.tvdb_id and _norm(media.tvdb_id) in by_tvdb:
        return by_tvdb[_norm(media.tvdb_id)]
    if media.tmdb_id and _norm(media.tmdb_id) in by_tmdb:
        return by_tmdb[_norm(media.tmdb_id)]
    if media.imdb_id and _norm(media.imdb_id) in by_imdb:
        return by_imdb[_norm(media.imdb_id)]
    return None


async def sync_sonarr(db: Session, integration: Integration) -> dict:
    # Reconcile Sonarr's complete local TV inventory into Apollo's catalog.
    # Sonarr remains authority only for local existence, source path, quality,
    # and stable external identity. Existing Apollo/TMDB presentation metadata
    # is never overwritten by Sonarr.
    headers = _headers(integration)
    base = _base_url(integration)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(f"{base}/api/v3/series", headers=headers)
        response.raise_for_status()
        series_rows = response.json()

        existing = list(
            db.scalars(
                select(Media).where(
                    Media.media_type.in_(["show", "series", "tvshow", "episode"])
                )
            )
        )

        def identity_values(series: dict) -> tuple[str | None, str | None, str | None]:
            return (
                _norm(series.get("tvdbId")),
                _norm(series.get("tmdbId")),
                _norm(series.get("imdbId")),
            )

        def canonical_for(series: dict) -> str | None:
            tvdb, tmdb, imdb = identity_values(series)
            if tmdb:
                return f"tmdb:{tmdb}"
            if tvdb:
                return f"tvdb:{tvdb}"
            if imdb:
                return imdb
            return None

        def same_series(media: Media, series: dict) -> bool:
            tvdb, tmdb, imdb = identity_values(series)
            return bool(
                (tvdb and _norm(media.tvdb_id) == tvdb)
                or (tmdb and _norm(media.tmdb_id) == tmdb)
                or (imdb and _norm(media.imdb_id) == imdb)
            )

        def apply_missing_identity(media: Media, series: dict) -> None:
            if not media.tvdb_id and series.get("tvdbId"):
                media.tvdb_id = str(series.get("tvdbId"))
            if not media.tmdb_id and series.get("tmdbId"):
                media.tmdb_id = str(series.get("tmdbId"))
            if not media.imdb_id and series.get("imdbId"):
                media.imdb_id = str(series.get("imdbId"))

        seen: set[tuple] = set()
        matched = 0
        available = 0
        created_shows = 0
        created_episodes = 0

        for series in series_rows:
            series_id = series.get("id")
            canonical = canonical_for(series)
            if series_id is None or not canonical:
                continue

            show_row = next(
                (
                    media for media in existing
                    if media.media_type in ("show", "series", "tvshow")
                    and same_series(media, series)
                ),
                None,
            )
            if show_row is None:
                show_row = Media(
                    media_type="show",
                    canonical_id=canonical,
                    title=str(series.get("title") or "Unknown Show"),
                    series_title=str(series.get("title") or "Unknown Show"),
                    imdb_id=str(series.get("imdbId") or "") or None,
                    tmdb_id=str(series.get("tmdbId") or "") or None,
                    tvdb_id=str(series.get("tvdbId") or "") or None,
                    year=series.get("year"),
                )
                db.add(show_row)
                db.flush()
                existing.append(show_row)
                created_shows += 1
            else:
                apply_missing_identity(show_row, series)

            episodes_resp = await client.get(
                f"{base}/api/v3/episode",
                params={"seriesId": int(series_id)},
                headers=headers,
            )
            episodes_resp.raise_for_status()
            episodes = episodes_resp.json()

            files_resp = await client.get(
                f"{base}/api/v3/episodefile",
                params={"seriesId": int(series_id)},
                headers=headers,
            )
            files_resp.raise_for_status()
            episode_files = {
                int(f["id"]): f for f in files_resp.json()
                if f.get("id") is not None
            }

            for episode in episodes:
                season_number = int(episode.get("seasonNumber", -1))
                episode_number = int(episode.get("episodeNumber", -1))
                if season_number < 0 or episode_number < 0:
                    continue

                file_id = episode.get("episodeFileId")
                file_row = episode_files.get(int(file_id)) if file_id else None
                is_available = bool(episode.get("hasFile") and file_row)

                media = next(
                    (
                        candidate for candidate in existing
                        if candidate.media_type == "episode"
                        and int(candidate.season if candidate.season is not None else -1) == season_number
                        and int(candidate.episode if candidate.episode is not None else -1) == episode_number
                        and same_series(candidate, series)
                    ),
                    None,
                )

                if media is None and not is_available:
                    continue

                if media is None:
                    media = Media(
                        media_type="episode",
                        canonical_id=canonical,
                        title=str(episode.get("title") or f"Episode {episode_number}"),
                        series_title=str(series.get("title") or "Unknown Show"),
                        imdb_id=str(series.get("imdbId") or "") or None,
                        tmdb_id=str(series.get("tmdbId") or "") or None,
                        tvdb_id=str(series.get("tvdbId") or "") or None,
                        year=series.get("year"),
                        season=season_number,
                        episode=episode_number,
                    )
                    db.add(media)
                    db.flush()
                    existing.append(media)
                    created_episodes += 1
                else:
                    apply_missing_identity(media, series)

                matched += 1
                provider_item_id = str(episode.get("id"))
                source_path = (
                    _join_path(series.get("path"), file_row)
                    if is_available else ""
                )
                row = _upsert_local(
                    db,
                    media=media,
                    provider="sonarr",
                    provider_item_id=provider_item_id,
                    source_path=source_path,
                    available=is_available,
                    quality=_quality(file_row) if is_available else None,
                )
                seen.add((media.id, provider_item_id))
                if row.available:
                    available += 1

            stats = series.get("statistics") or {}
            show_available = bool(stats.get("episodeFileCount", 0))
            show_provider_id = f"series:{series_id}"
            show_local = _upsert_local(
                db,
                media=show_row,
                provider="sonarr",
                provider_item_id=show_provider_id,
                source_path=(series.get("path") or "") if show_available else "",
                available=show_available,
                quality=None,
            )
            seen.add((show_row.id, show_provider_id))
            if show_local.available:
                available += 1

    stale = _mark_provider_stale(db, "sonarr", seen)
    db.commit()
    return {
        "provider": "sonarr",
        "matched": matched,
        "available": available,
        "created_shows": created_shows,
        "created_episodes": created_episodes,
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

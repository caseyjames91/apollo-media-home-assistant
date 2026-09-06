from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.models.media import Media
from app.models.progress import Progress
from app.services.episodes import materialize_season
from app.services.tmdb import DEFAULT_BASE_URL, TMDB_KIND, _headers


EPISODE_CANONICAL_RE = re.compile(
    r"^tmdb:(?P<series>\d+):s(?P<season>\d+)e(?P<episode>\d+)$"
)


def _integration(db: Session) -> Integration:
    integration = db.scalar(
        select(Integration).where(
            Integration.kind == TMDB_KIND,
            Integration.enabled.is_(True),
        )
    )
    if integration is None or not integration.access_token:
        raise HTTPException(
            status_code=503,
            detail="TMDB is not configured",
        )
    return integration


def _base(integration: Integration) -> str:
    return (integration.base_url or DEFAULT_BASE_URL).rstrip("/")


async def _tmdb_json(
    integration: Integration,
    path: str,
    params: dict | None = None,
) -> dict:
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            f"{_base(integration)}{path}",
            headers=_headers(integration),
            params=params or {},
        )
        response.raise_for_status()
        return response.json() or {}


def _parsed_episode_identity(
    media: Media,
) -> tuple[str, int, int] | None:
    match = EPISODE_CANONICAL_RE.match(
        str(media.canonical_id or "").strip()
    )
    if not match:
        return None

    return (
        match.group("series"),
        int(match.group("season")),
        int(match.group("episode")),
    )


async def _series_tmdb_id(
    db: Session,
    media: Media,
    integration: Integration,
) -> str | None:
    parsed = _parsed_episode_identity(media)
    if parsed:
        return parsed[0]

    imdb_id = str(media.imdb_id or "").strip()
    if not imdb_id:
        return None

    existing_show = db.scalar(
        select(Media).where(
            Media.media_type == "show",
            Media.imdb_id == imdb_id,
            Media.tmdb_id.is_not(None),
        ).limit(1)
    )
    if existing_show and existing_show.tmdb_id:
        return str(existing_show.tmdb_id)

    raw = await _tmdb_json(
        integration,
        f"/find/{imdb_id}",
        {"external_source": "imdb_id"},
    )
    results = raw.get("tv_results") or []
    if not results:
        return None

    return str(results[0].get("id") or "").strip() or None


def _image_url(path: str | None) -> str | None:
    from app.services.tmdb import IMAGE_BASE_URL

    value = str(path or "").strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return IMAGE_BASE_URL + (
        value if value.startswith("/") else "/" + value
    )


def _normal_seasons(show_raw: dict) -> list[int]:
    seasons = []

    for raw in show_raw.get("seasons") or []:
        number = int(raw.get("season_number") or 0)
        if number <= 0:
            continue
        seasons.append(number)

    return sorted(set(seasons))


def _is_future_episode(air_date: str | None) -> bool:
    value = str(air_date or "").strip()
    if not value:
        return False

    try:
        return date.fromisoformat(value) > date.today()
    except ValueError:
        return False


def _profile_progress(
    db: Session,
    profile_id: uuid.UUID,
    media_id: uuid.UUID,
) -> Progress | None:
    return db.scalar(
        select(Progress).where(
            Progress.profile_id == profile_id,
            Progress.media_id == media_id,
        )
    )


def _episode_result(
    db: Session,
    profile_id: uuid.UUID,
    media: Media,
    *,
    air_date: str | None = None,
    available_locally: bool = False,
    source_updated_at: datetime | None = None,
) -> dict:
    progress = _profile_progress(
        db,
        profile_id,
        media.id,
    )

    expected = int(media.runtime_seconds or 0)
    position = (
        int(progress.position_seconds or 0)
        if progress
        else 0
    )
    observed_duration = (
        int(progress.duration_seconds or 0)
        if progress
        else 0
    )
    denominator = expected or observed_duration

    return {
        "media_id": str(media.id),
        "media_type": "episode",
        "canonical_id": media.canonical_id,
        "imdb_id": media.imdb_id,
        "tmdb_id": media.tmdb_id,
        "series_title": media.series_title,
        "title": media.title,
        "season": media.season,
        "episode": media.episode,
        "overview": media.overview,
        "poster_url": media.poster_url,
        "backdrop_url": media.backdrop_url,
        "air_date": air_date,
        "runtime": (
            int(expected / 60)
            if expected > 0
            else None
        ),
        "expected_duration_seconds": (
            expected or None
        ),
        "position_seconds": position,
        "duration_seconds": (
            observed_duration or None
        ),
        "progress_fraction": (
            position / denominator
            if denominator > 0
            else 0.0
        ),
        "watched": bool(progress.watched)
        if progress
        else False,
        "available_locally": available_locally,
        "source_updated_at": source_updated_at,
    }


async def next_episode_after(
    db: Session,
    profile_id: uuid.UUID,
    media: Media,
) -> dict | None:
    """
    Return the next canonical unwatched aired episode after `media`.

    This resolver owns episode ordering. It materializes missing seasons through
    TMDB before choosing a target, so crossing a season boundary does not depend
    on whether that season has previously been browsed in Discovery.
    """
    if media.media_type != "episode":
        return None

    integration = _integration(db)
    series_tmdb_id = await _series_tmdb_id(
        db,
        media,
        integration,
    )
    if not series_tmdb_id:
        return None

    parsed = _parsed_episode_identity(media)
    current_season = int(
        media.season
        or (parsed[1] if parsed else 0)
        or 0
    )
    current_episode = int(
        media.episode
        or (parsed[2] if parsed else 0)
        or 0
    )

    show_raw = await _tmdb_json(
        integration,
        f"/tv/{series_tmdb_id}",
        {"append_to_response": "external_ids"},
    )

    external = show_raw.get("external_ids") or {}
    show_imdb_id = (
        str(
            external.get("imdb_id")
            or media.imdb_id
            or ""
        ).strip()
        or None
    )
    series_title = str(
        show_raw.get("name")
        or media.series_title
        or ""
    )
    show_poster_url = (
        _image_url(show_raw.get("poster_path"))
        or media.poster_url
    )
    show_backdrop_url = (
        _image_url(show_raw.get("backdrop_path"))
        or media.backdrop_url
    )
    show_runtime = next(
        (
            int(value)
            for value in (
                show_raw.get("episode_run_time") or []
            )
            if int(value or 0) > 0
        ),
        0,
    )

    seasons = _normal_seasons(show_raw)

    for season_number in seasons:
        if season_number < current_season:
            continue

        season_raw = await _tmdb_json(
            integration,
            f"/tv/{series_tmdb_id}/season/{season_number}",
        )
        materialized = materialize_season(
            db,
            series_tmdb_id=str(series_tmdb_id),
            show_imdb_id=show_imdb_id,
            series_title=series_title,
            show_poster_url=show_poster_url,
            show_backdrop_url=show_backdrop_url,
            season_number=season_number,
            season_raw=season_raw,
            show_runtime_minutes=show_runtime,
        )

        for item in materialized:
            candidate_key = (
                int(item["season"]),
                int(item["episode"]),
            )
            current_key = (
                current_season,
                current_episode,
            )

            if candidate_key <= current_key:
                continue

            if _is_future_episode(item.get("air_date")):
                continue

            candidate = db.get(
                Media,
                uuid.UUID(item["media_id"]),
            )
            if candidate is None:
                continue

            progress = _profile_progress(
                db,
                profile_id,
                candidate.id,
            )
            if progress and progress.watched:
                continue

            db.commit()

            return _episode_result(
                db,
                profile_id,
                candidate,
                air_date=item.get("air_date"),
                available_locally=bool(
                    item.get("available_locally")
                ),
            )

    db.commit()
    return None


async def profile_next_up(
    db: Session,
    profile_id: uuid.UUID,
) -> list[dict]:
    """
    Build the persistent profile-owned Next Up feed.

    Continue Watching and Next Up intentionally remain separate engines:
    only a show's most recent *completed* episode advances that show here.
    An unfinished latest episode remains owned by Continue Watching.
    """
    rows = db.execute(
        select(Progress, Media)
        .join(Media, Media.id == Progress.media_id)
        .where(
            Progress.profile_id == profile_id,
            Media.media_type == "episode",
        )
        .order_by(Progress.updated_at.desc())
    ).all()

    latest_by_series: dict[str, tuple[Progress, Media]] = {}

    for progress, media in rows:
        parsed = _parsed_episode_identity(media)
        if parsed:
            series_key = f"tmdb:{parsed[0]}"
        else:
            imdb_id = str(media.imdb_id or "").strip()
            if not imdb_id:
                continue
            series_key = f"imdb:{imdb_id}"

        if series_key not in latest_by_series:
            latest_by_series[series_key] = (
                progress,
                media,
            )

    out: list[dict] = []

    for progress, media in latest_by_series.values():
        # If the latest profile state for this show is unfinished,
        # Continue Watching owns the row presentation.
        if not progress.watched:
            continue

        target = await next_episode_after(
            db,
            profile_id,
            media,
        )
        if target is None:
            continue

        target["state"] = "next_up"
        target["source_updated_at"] = progress.updated_at
        out.append(target)

    epoch = datetime.min.replace(tzinfo=timezone.utc)

    out.sort(
        key=lambda item: (
            item.get("source_updated_at") or epoch
        ),
        reverse=True,
    )

    return out

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.services.tmdb import IMAGE_BASE_URL


def _image(path) -> str | None:
    value = str(path or "").strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return IMAGE_BASE_URL + (value if value.startswith("/") else "/" + value)


def _local(db: Session, media: Media | None) -> bool:
    if media is None:
        return False

    return db.scalar(
        select(LocalAvailability.id).where(
            LocalAvailability.media_id == media.id,
            LocalAvailability.available.is_(True),
        ).limit(1)
    ) is not None


def materialize_season(
    db: Session,
    *,
    series_tmdb_id: str,
    show_imdb_id: str | None,
    series_title: str,
    show_poster_url: str | None,
    show_backdrop_url: str | None,
    season_number: int,
    season_raw: dict,
    show_runtime_minutes: int = 0,
) -> list[dict]:
    """
    Reconcile one TMDB season into Apollo canonical episode rows.

    This is shared infrastructure for both Discovery and profile-owned Next Up.
    Canonical episode identity belongs to Apollo; TMDB only supplies canonical
    catalog/order metadata.
    """
    season_number = int(season_number)
    episodes: list[dict] = []

    for raw in season_raw.get("episodes") or []:
        episode_number = int(raw.get("episode_number") or 0)
        if episode_number <= 0:
            continue

        canonical_id = (
            f"tmdb:{series_tmdb_id}:s{season_number}e{episode_number}"
        )
        runtime_minutes = int(
            raw.get("runtime") or show_runtime_minutes or 0
        )

        canonical = db.scalar(
            select(Media).where(
                Media.media_type == "episode",
                Media.canonical_id == canonical_id,
                Media.season == season_number,
                Media.episode == episode_number,
            )
        )

        if canonical is None:
            canonical = Media(
                media_type="episode",
                canonical_id=canonical_id,
                imdb_id=show_imdb_id,
                tmdb_id=str(raw.get("id") or "") or None,
                title=str(
                    raw.get("name") or f"Episode {episode_number}"
                ),
                series_title=series_title,
                overview=raw.get("overview"),
                poster_url=(
                    _image(raw.get("still_path"))
                    or show_poster_url
                ),
                backdrop_url=show_backdrop_url,
                season=season_number,
                episode=episode_number,
            )
            db.add(canonical)
            db.flush()
        else:
            canonical.imdb_id = show_imdb_id or canonical.imdb_id
            canonical.tmdb_id = (
                str(raw.get("id") or "")
                or canonical.tmdb_id
            )
            canonical.title = (
                str(raw.get("name") or "")
                or canonical.title
            )
            canonical.series_title = (
                series_title or canonical.series_title
            )
            canonical.overview = (
                raw.get("overview") or canonical.overview
            )
            canonical.poster_url = (
                _image(raw.get("still_path"))
                or show_poster_url
                or canonical.poster_url
            )
            canonical.backdrop_url = (
                show_backdrop_url or canonical.backdrop_url
            )

        if runtime_minutes > 0:
            canonical.runtime_seconds = runtime_minutes * 60

        episodes.append(
            {
                "media_id": str(canonical.id),
                "media_type": "episode",
                "canonical_id": canonical.canonical_id,
                "imdb_id": canonical.imdb_id,
                "tmdb_id": canonical.tmdb_id,
                "series_tmdb_id": str(series_tmdb_id),
                "series_title": canonical.series_title,
                "title": canonical.title,
                "season": season_number,
                "episode": episode_number,
                "overview": canonical.overview,
                "poster_url": canonical.poster_url,
                "backdrop_url": canonical.backdrop_url,
                "air_date": raw.get("air_date"),
                # Preserve the existing Discovery response contract:
                # these values describe the current provider observation, not
                # an older canonical runtime already stored on the Media row.
                "runtime": runtime_minutes,
                "expected_duration_seconds": runtime_minutes * 60,
                "available_locally": _local(db, canonical),
            }
        )

    return episodes

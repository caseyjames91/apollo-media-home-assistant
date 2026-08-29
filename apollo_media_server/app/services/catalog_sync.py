from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.models.sync_state import SyncState
from app.services.jellyfin import fetch_sync_payload, parse_jellyfin_datetime, ticks_to_seconds


def _provider_ids(item: dict) -> dict:
    return item.get("ProviderIds") or {}


def _canonical_for_item(item: dict, series_identity: dict[str, str] | None = None) -> tuple[str, str | None, str | None]:
    providers = _provider_ids(item)
    imdb = providers.get("Imdb") or providers.get("IMDb")
    tmdb = providers.get("Tmdb") or providers.get("TMDb")
    item_id = str(item.get("Id") or "")

    if item.get("Type") == "Episode" and series_identity:
        canonical = series_identity.get("imdb") or series_identity.get("tmdb") or series_identity.get("jellyfin") or item_id
        return canonical, series_identity.get("imdb"), series_identity.get("tmdb")

    return imdb or tmdb or item_id, imdb, tmdb


def _media_type(item: dict) -> str:
    kind = item.get("Type")
    return {"Movie": "movie", "Series": "show", "Episode": "episode"}.get(kind, str(kind or "video").lower())


def _find_media(db: Session, media_type: str, canonical_id: str, season: int | None, episode: int | None) -> Media | None:
    q = select(Media).where(Media.media_type == media_type, Media.canonical_id == canonical_id)
    q = q.where(Media.season.is_(None) if season is None else Media.season == season)
    q = q.where(Media.episode.is_(None) if episode is None else Media.episode == episode)
    return db.scalar(q)


def _upsert_media(db: Session, item: dict, series_identity: dict[str, str] | None = None) -> Media:
    media_type = _media_type(item)
    season = item.get("ParentIndexNumber") if media_type == "episode" else None
    episode = item.get("IndexNumber") if media_type == "episode" else None
    canonical_id, imdb, tmdb = _canonical_for_item(item, series_identity)
    jellyfin_id = str(item.get("Id") or "") or None
    title = item.get("Name") or "Untitled"

    media = _find_media(db, media_type, canonical_id, season, episode)
    if media is None:
        media = Media(
            media_type=media_type,
            canonical_id=canonical_id,
            imdb_id=imdb,
            tmdb_id=tmdb,
            jellyfin_item_id=jellyfin_id,
            title=title,
            season=season,
            episode=episode,
        )
        db.add(media)
        db.flush()
    else:
        media.imdb_id = imdb or media.imdb_id
        media.tmdb_id = tmdb or media.tmdb_id
        media.jellyfin_item_id = jellyfin_id or media.jellyfin_item_id
        media.title = title
    return media


async def sync_jellyfin(db: Session) -> dict:
    integration = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    if integration is None or not integration.enabled or not integration.access_token or not integration.user_id:
        raise RuntimeError("Jellyfin is not configured")

    profile = db.scalar(select(Profile).where(Profile.jellyfin_user_id == integration.user_id))
    if profile is None:
        raise RuntimeError("No Apollo profile is mapped to the Jellyfin user")

    state = db.scalar(select(SyncState).where(SyncState.integration_kind == "jellyfin"))
    if state is None:
        state = SyncState(integration_kind="jellyfin")
        db.add(state)
        db.flush()

    # Network work happens first. A failure here leaves catalog/progress untouched.
    try:
        payload = await fetch_sync_payload(integration.base_url, integration.user_id, integration.access_token)
    except Exception as exc:
        state.last_error_at = datetime.now(timezone.utc)
        state.last_error = str(exc)[:4000]
        db.commit()
        raise

    series_by_jellyfin_id: dict[str, dict[str, str]] = {}
    for item in payload.catalog_items:
        if item.get("Type") != "Series":
            continue
        providers = _provider_ids(item)
        series_by_jellyfin_id[str(item.get("Id") or "")] = {
            "imdb": providers.get("Imdb") or providers.get("IMDb"),
            "tmdb": providers.get("Tmdb") or providers.get("TMDb"),
            "jellyfin": str(item.get("Id") or ""),
        }

    try:
        catalog_count = 0
        for item in payload.catalog_items:
            if item.get("Type") not in {"Movie", "Series"}:
                continue
            _upsert_media(db, item)
            catalog_count += 1

        resume_count = 0
        for item in payload.resume_items:
            kind = item.get("Type")
            if kind not in {"Movie", "Episode"}:
                continue
            series_identity = None
            if kind == "Episode":
                series_identity = series_by_jellyfin_id.get(str(item.get("SeriesId") or ""))
            media = _upsert_media(db, item, series_identity)
            user_data = item.get("UserData") or {}
            position = ticks_to_seconds(user_data.get("PlaybackPositionTicks"))
            duration = ticks_to_seconds(item.get("RunTimeTicks"))
            if position <= 0:
                continue

            progress = db.scalar(select(Progress).where(
                Progress.profile_id == profile.id,
                Progress.media_id == media.id,
            ))
            if progress is None:
                progress = Progress(profile_id=profile.id, media_id=media.id)
                db.add(progress)

            jellyfin_updated = parse_jellyfin_datetime(user_data.get("LastPlayedDate"))
            existing_updated = progress.updated_at
            if existing_updated is not None and existing_updated.tzinfo is None:
                existing_updated = existing_updated.replace(tzinfo=timezone.utc)
            if jellyfin_updated.tzinfo is None:
                jellyfin_updated = jellyfin_updated.replace(tzinfo=timezone.utc)
            # AMS is the profile authority. A stale Jellyfin snapshot must never
            # overwrite newer remote/Kodi progress already reported to AMS.
            if existing_updated is None or jellyfin_updated >= existing_updated:
                progress.position_seconds = position
                progress.duration_seconds = duration
                progress.updated_at = jellyfin_updated
            resume_count += 1

        state.last_success_at = datetime.now(timezone.utc)
        state.last_error = None
        state.catalog_items = catalog_count
        state.continue_watching_items = resume_count
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "status": "ok",
        "catalog_items": catalog_count,
        "continue_watching_items": resume_count,
        "profile_id": str(profile.id),
        "last_success_at": state.last_success_at.isoformat() if state.last_success_at else None,
    }

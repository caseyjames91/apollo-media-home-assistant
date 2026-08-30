import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.local_availability import LocalAvailability
from app.models.media import Media
from app.models.path_mapping import PathMapping
from app.schemas.local import LocalSourceUpsert, PathMappingCreate, PathMappingRead
from app.services.arr import sync_local_availability


router = APIRouter(tags=["local"])


def resolve_path(db: Session, source_path: str, device_key: str = "*") -> str | None:
    mappings = list(
        db.scalars(
            select(PathMapping).where(
                PathMapping.device_key.in_([device_key, "*"])
            )
        )
    )
    # Device-specific mappings win over wildcard mappings. Within each scope,
    # the most specific source prefix wins.
    mappings.sort(key=lambda m: (m.device_key != device_key, -len(m.source_prefix)))

    normalized = source_path.replace("\\", "/")
    for mapping in mappings:
        source = mapping.source_prefix.replace("\\", "/").rstrip("/")
        if normalized == source or normalized.startswith(source + "/"):
            suffix = normalized[len(source):].lstrip("/")
            return mapping.kodi_prefix.rstrip("/") + ("/" + suffix if suffix else "")
    return None


def _available_sources(db: Session, media_id: uuid.UUID) -> list[LocalAvailability]:
    return list(
        db.scalars(
            select(LocalAvailability)
            .where(
                LocalAvailability.media_id == media_id,
                LocalAvailability.available.is_(True),
            )
            .order_by(LocalAvailability.provider, LocalAvailability.provider_item_id)
        )
    )


@router.post("/path-mappings", response_model=PathMappingRead, status_code=201)
def create_mapping(payload: PathMappingCreate, db: Session = Depends(get_db)):
    row = PathMapping(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/path-mappings", response_model=list[PathMappingRead])
def list_mappings(db: Session = Depends(get_db)):
    return list(db.scalars(select(PathMapping).order_by(PathMapping.name)))


@router.get("/path-mappings/resolve")
def resolve_mapping(
    source_path: str,
    device_key: str = "*",
    db: Session = Depends(get_db),
):
    return {
        "source_path": source_path,
        "device_key": device_key,
        "playback_path": resolve_path(db, source_path, device_key),
    }


@router.get("/media/{media_id}/playback-resolution")
def playback_resolution(
    media_id: uuid.UUID,
    device_key: str,
    db: Session = Depends(get_db),
):
    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")

    local_sources = _available_sources(db, media_id)
    unresolved = []

    for source in local_sources:
        if not source.source_path:
            unresolved.append(
                {
                    "provider": source.provider,
                    "provider_item_id": source.provider_item_id,
                    "source_path": None,
                    "quality": source.quality,
                    "reason": "provider_did_not_report_file_path",
                }
            )
            continue

        playback_path = resolve_path(db, source.source_path, device_key)
        if playback_path:
            return {
                "media_id": str(media.id),
                "device_key": device_key,
                "available_locally": True,
                "mode": "local",
                "provider": source.provider,
                "provider_item_id": source.provider_item_id,
                "source_path": source.source_path,
                "playback_path": playback_path,
                "quality": source.quality,
                "fallback_required": False,
                "reason": None,
            }

        unresolved.append(
            {
                "provider": source.provider,
                "provider_item_id": source.provider_item_id,
                "source_path": source.source_path,
                "quality": source.quality,
                "reason": "no_path_mapping_for_device",
            }
        )

    if local_sources:
        return {
            "media_id": str(media.id),
            "device_key": device_key,
            "available_locally": True,
            "mode": "remote",
            "provider": None,
            "provider_item_id": None,
            "source_path": None,
            "playback_path": None,
            "quality": None,
            "fallback_required": True,
            "reason": "local_path_unresolved",
            "unresolved_local_sources": unresolved,
        }

    return {
        "media_id": str(media.id),
        "device_key": device_key,
        "available_locally": False,
        "mode": "remote",
        "provider": None,
        "provider_item_id": None,
        "source_path": None,
        "playback_path": None,
        "quality": None,
        "fallback_required": True,
        "reason": "not_available_locally",
        "unresolved_local_sources": [],
    }


@router.post("/local-availability")
def upsert_local_source(payload: LocalSourceUpsert, db: Session = Depends(get_db)):
    if db.get(Media, payload.media_id) is None:
        raise HTTPException(status_code=404, detail="Media not found")

    kodi_path = resolve_path(db, payload.source_path, payload.device_key)
    q = select(LocalAvailability).where(
        LocalAvailability.media_id == payload.media_id,
        LocalAvailability.provider == payload.provider,
        LocalAvailability.provider_item_id == payload.provider_item_id,
    )
    row = db.scalar(q)

    # Manual writes remain supported for development, but availability no longer
    # depends on whether a Kodi path mapping happens to exist.
    values = dict(
        provider=payload.provider,
        provider_item_id=payload.provider_item_id,
        source_path=payload.source_path,
        kodi_path=kodi_path or "",
        available=True,
        quality=payload.quality,
        updated_at=datetime.now(timezone.utc),
    )
    if row is None:
        row = LocalAvailability(media_id=payload.media_id, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return {
        "media_id": str(payload.media_id),
        "available_locally": row.available,
        "kodi_path": row.kodi_path or None,
    }


@router.post("/local-availability/sync")
async def sync_arr_local_availability(db: Session = Depends(get_db)):
    try:
        return await sync_local_availability(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Local availability sync failed: {exc}") from exc

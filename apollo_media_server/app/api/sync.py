from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sync_state import SyncState
from app.services.catalog_sync import sync_jellyfin
from app.services.tmdb import sync_metadata

router = APIRouter(tags=["sync"])


@router.post("/jellyfin/sync")
async def jellyfin_sync(db: Session = Depends(get_db)):
    try:
        return await sync_jellyfin(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jellyfin sync failed: {exc}") from exc


@router.get("/jellyfin/sync/status")
def jellyfin_sync_status(db: Session = Depends(get_db)):
    state = db.scalar(select(SyncState).where(SyncState.integration_kind == "jellyfin"))
    if state is None:
        return {"configured": True, "last_success_at": None, "catalog_items": 0, "continue_watching_items": 0, "last_error": None}
    return {
        "configured": True,
        "last_success_at": state.last_success_at,
        "last_error_at": state.last_error_at,
        "last_error": state.last_error,
        "catalog_items": state.catalog_items,
        "continue_watching_items": state.continue_watching_items,
    }



@router.post("/metadata/sync")
async def metadata_sync(db: Session = Depends(get_db)):
    try:
        return await sync_metadata(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata sync failed: {exc}") from exc

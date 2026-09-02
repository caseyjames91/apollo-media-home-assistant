from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.tmdb import sync_metadata

router = APIRouter(tags=["sync"])


@router.post("/metadata/sync")
async def metadata_sync(db: Session = Depends(get_db)):
    try:
        return await sync_metadata(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata sync failed: {exc}") from exc

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import get_db

from app.services import youtube as youtube_service


router = APIRouter(prefix="/youtube", tags=["youtube"])

class YouTubePlayRequest(BaseModel):
    device_key: str
    video_id: str
    start_seconds: float | None = None


@router.get("/status")
async def youtube_status():
    return await youtube_service.status()


@router.get("/home")
async def youtube_home():
    try:
        return await youtube_service.home()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"YouTube Home failed: {exc}",
        ) from exc


@router.get("/history")
async def youtube_history():
    try:
        return await youtube_service.history()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"YouTube History failed: {exc}",
        ) from exc

@router.get("/continue-watching")
async def youtube_continue_watching():
    try:
        return await youtube_service.continue_watching()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"YouTube Continue Watching failed: {exc}",
        ) from exc

@router.post("/play")
async def youtube_play(
    payload: YouTubePlayRequest,
    db: Session = Depends(get_db),
):
    try:
        return await youtube_service.play(
            db,
            payload.device_key,
            payload.video_id,
            payload.start_seconds,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"YouTube playback failed: {exc}",
        ) from exc

@router.post("/import-cookie")
async def youtube_import_cookie(
    request: Request,
    x_apollo_import_key: str | None = Header(default=None),
):
    expected = os.getenv("APOLLO_YOUTUBE_IMPORT_KEY")
    if not expected or x_apollo_import_key != expected:
        raise HTTPException(status_code=403, detail="Invalid import key")

    path = Path("/config/youtube-cookie.txt")
    if path.exists():
        raise HTTPException(status_code=409, detail="YouTube cookie already configured")

    cookie = (await request.body()).decode("utf-8").strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="Empty cookie")

    path.write_text(cookie + "\n", encoding="utf-8")
    path.chmod(0o600)

    return {"configured": True}

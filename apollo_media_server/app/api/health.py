from app.core.config import settings
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok", "service": "apollo-media-server", "version": settings.version}

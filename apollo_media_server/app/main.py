from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import devices, health, local, media, profiles, progress, sessions
from app.db.session import init_db
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Apollo Media Server", version=settings.version,
              description="Apollo-owned profiles, media state, progress, local availability, and playback sessions",
              lifespan=lifespan)
app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(devices.router)
app.include_router(media.router)
app.include_router(progress.router)
app.include_router(local.router)
app.include_router(sessions.router)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import devices, discovery, health, integrations, local, media, profiles, progress, sessions, sync, youtube
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Apollo Media Server",
    version=settings.version,
    description="Apollo-owned profiles, media state, progress, local availability, and playback sessions",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hass.apollo.home",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(devices.router)
app.include_router(media.router)
app.include_router(discovery.router)
app.include_router(progress.router)
app.include_router(integrations.router)
app.include_router(sync.router)
app.include_router(local.router)
app.include_router(sessions.router)
app.include_router(youtube.router)

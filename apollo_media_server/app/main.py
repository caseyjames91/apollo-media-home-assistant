from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import catalog, devices, health, profiles, progress, setup, sync, debug
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Apollo Media Server",
    version="0.1.5",
    description="Central catalog/profile/device state service for Apollo Media",
    lifespan=lifespan,
)

app.include_router(setup.router)
app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(devices.router)
app.include_router(progress.router)
app.include_router(catalog.router)
app.include_router(sync.router)
app.include_router(debug.router)

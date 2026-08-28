import uuid
from datetime import datetime
from pydantic import BaseModel

class ProgressUpsert(BaseModel):
    profile_id: uuid.UUID
    media_type: str
    canonical_id: str
    title: str
    imdb_id: str | None = None
    tmdb_id: str | None = None
    jellyfin_item_id: str | None = None
    season: int | None = None
    episode: int | None = None
    position_seconds: float
    duration_seconds: float

class ContinueWatchingItem(BaseModel):
    media_id: uuid.UUID
    media_type: str
    canonical_id: str
    title: str
    series_title: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    jellyfin_item_id: str | None = None
    artwork_jellyfin_item_id: str | None = None
    season: int | None = None
    episode: int | None = None
    position_seconds: float
    duration_seconds: float
    progress_fraction: float
    updated_at: datetime

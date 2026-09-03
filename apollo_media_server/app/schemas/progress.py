import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ProgressUpsert(BaseModel):
    profile_id: uuid.UUID
    media_type: str
    canonical_id: str
    title: str
    series_title: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    season: int | None = None
    episode: int | None = None
    position_seconds: float
    duration_seconds: float
    updated_at: datetime | None = None


class ProgressImportItem(BaseModel):
    media_type: str
    canonical_id: str
    title: str
    series_title: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    season: int | None = None
    episode: int | None = None
    position_seconds: float
    duration_seconds: float
    updated_at: datetime | None = None


class ProgressImport(BaseModel):
    profile_id: uuid.UUID
    items: list[ProgressImportItem] = Field(default_factory=list, max_length=200)


class ContinueWatchingItem(BaseModel):
    media_id: uuid.UUID
    media_type: str
    canonical_id: str
    title: str
    series_title: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    season: int | None = None
    episode: int | None = None
    position_seconds: float
    duration_seconds: float
    progress_fraction: float
    runtime: int | None = None
    expected_duration_seconds: int | None = None
    available_locally: bool = False
    local_playback_path: str | None = None
    updated_at: datetime

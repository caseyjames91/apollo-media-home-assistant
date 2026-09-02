import uuid
from pydantic import BaseModel, ConfigDict


class MediaCreate(BaseModel):
    media_type: str
    canonical_id: str
    title: str
    series_title: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None


class MediaRead(MediaCreate):
    id: uuid.UUID
    available_locally: bool = False
    local_playback_path: str | None = None
    model_config = ConfigDict(from_attributes=True)

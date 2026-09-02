import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PlaybackSessionStart(BaseModel):
    profile_id: uuid.UUID
    media_id: uuid.UUID
    device_key: str
    source_type: str
    position_seconds: float = 0
    duration_seconds: float = 0


class PlaybackSessionUpdate(BaseModel):
    state: str | None = None
    position_seconds: float | None = None
    duration_seconds: float | None = None
    ended: bool = False


class PlaybackSessionRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    media_id: uuid.UUID
    device_key: str
    source_type: str
    state: str
    position_seconds: float
    duration_seconds: float
    started_at: datetime
    updated_at: datetime
    ended_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

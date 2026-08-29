import uuid
from pydantic import BaseModel, ConfigDict, Field


class PathMappingCreate(BaseModel):
    name: str
    device_key: str = "*"
    source_prefix: str = Field(min_length=1)
    kodi_prefix: str = Field(min_length=1)


class PathMappingRead(PathMappingCreate):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class LocalSourceUpsert(BaseModel):
    media_id: uuid.UUID
    provider: str
    provider_item_id: str
    source_path: str
    quality: str | None = None
    device_key: str = "*"

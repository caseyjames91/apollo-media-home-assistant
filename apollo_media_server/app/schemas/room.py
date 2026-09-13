import uuid

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_integration_id: uuid.UUID | None = None
    source_area_id: str | None = None
    sort_order: int = 0
    enabled: bool = True


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    source_integration_id: uuid.UUID | None = None
    source_area_id: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None


class RoomRead(RoomCreate):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

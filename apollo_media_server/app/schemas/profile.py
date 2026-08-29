import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    profile_type: str = "adult"
    avatar: str | None = None
    pin_required: bool = False


class ProfileRead(ProfileCreate):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

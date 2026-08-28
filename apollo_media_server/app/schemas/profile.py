import uuid
from pydantic import BaseModel, ConfigDict

class ProfileCreate(BaseModel):
    name: str
    jellyfin_user_id: str | None = None

class ProfileRead(ProfileCreate):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

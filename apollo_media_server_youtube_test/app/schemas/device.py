import uuid
from pydantic import BaseModel, ConfigDict

class DeviceRegister(BaseModel):
    name: str
    device_key: str
    device_type: str = "kodi"
    ha_entity_id: str | None = None
    kodi_jsonrpc_url: str | None = None

class DeviceRead(DeviceRegister):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

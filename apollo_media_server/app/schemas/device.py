import uuid

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegister(BaseModel):
    name: str
    device_key: str
    device_type: str = "kodi"
    ha_entity_id: str | None = None


class DeviceImport(BaseModel):
    integration_id: uuid.UUID
    source_device_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    device_type: str
    source_name: str | None = None
    room_id: uuid.UUID | None = None
    capabilities: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    room_id: uuid.UUID | None = None
    enabled: bool | None = None
    config: dict | None = None


class DeviceRead(BaseModel):
    id: uuid.UUID
    name: str
    device_key: str
    device_type: str
    ha_entity_id: str | None = None
    integration_id: uuid.UUID | None = None
    source_device_id: str | None = None
    source_name: str | None = None
    room_id: uuid.UUID | None = None
    capabilities: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    enabled: bool = True

    model_config = ConfigDict(from_attributes=True)


class AndroidTVPairStartResult(BaseModel):
    device_id: uuid.UUID
    pairing_started: bool
    message: str


class AndroidTVPairFinish(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class AndroidTVPairFinishResult(BaseModel):
    device_id: uuid.UUID
    paired: bool


class DeviceCommand(BaseModel):
    command: str


class DeviceLaunch(BaseModel):
    target: str = Field(min_length=1)


class AndroidTVState(BaseModel):
    device_id: uuid.UUID
    available: bool
    is_on: bool | None = None
    current_app: str | None = None
    volume: dict | None = None
    device_info: dict | None = None

import uuid

from pydantic import BaseModel, Field


class IntegrationTypeRead(BaseModel):
    kind: str
    name: str
    description: str
    discovery: bool
    pairing: bool
    control: bool
    requires_base_url: bool
    requires_access_token: bool


class IntegrationUpsert(BaseModel):
    kind: str
    name: str = "default"
    base_url: str = ""
    access_token: str | None = None
    refresh_token: str | None = None
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class IntegrationRead(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    base_url: str
    config: dict = Field(default_factory=dict)
    enabled: bool
    configured: bool = True


class IntegrationTestResult(BaseModel):
    kind: str
    name: str
    ok: bool
    server_name: str | None = None
    version: str | None = None


class DiscoveredDevice(BaseModel):
    source_device_id: str
    name: str
    host: str
    port: int
    model: str | None = None
    mac: str | None = None
    certificate_name: str | None = None
    stable_identity: bool = False
    integration_kind: str = "android_tv"

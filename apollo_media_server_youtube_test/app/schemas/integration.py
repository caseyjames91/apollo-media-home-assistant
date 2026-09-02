from pydantic import BaseModel, Field


class IntegrationUpsert(BaseModel):
    kind: str
    name: str = "default"
    base_url: str
    access_token: str = Field(min_length=1)
    enabled: bool = True


class IntegrationRead(BaseModel):
    kind: str
    name: str
    base_url: str
    enabled: bool
    configured: bool = True


class IntegrationTestResult(BaseModel):
    kind: str
    name: str
    ok: bool
    server_name: str | None = None
    version: str | None = None

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.registry import INTEGRATION_TYPES, get_integration_type
from app.models.integration import Integration
from app.schemas.integration import (
    DiscoveredDevice,
    IntegrationRead,
    IntegrationTestResult,
    IntegrationTypeRead,
    IntegrationUpsert,
)
from app.services.android_tv import discover_android_tv_devices
from app.services.arr import SUPPORTED_KINDS as ARR_SUPPORTED_KINDS, test_integration as test_arr_integration
from app.services.tmdb import TMDB_KIND, test_integration as test_tmdb_integration


router = APIRouter(prefix="/integrations", tags=["integrations"])


def _config(row: Integration) -> dict:
    try:
        value = json.loads(row.config_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read(row: Integration) -> IntegrationRead:
    integration_type = get_integration_type(row.kind)
    configured = True
    if integration_type is not None:
        if integration_type.requires_base_url and not row.base_url:
            configured = False
        if integration_type.requires_access_token and not row.access_token:
            configured = False

    return IntegrationRead(
        id=row.id,
        kind=row.kind,
        name=row.name,
        base_url=row.base_url,
        config=_config(row),
        enabled=row.enabled,
        configured=configured,
    )


@router.get("/types", response_model=list[IntegrationTypeRead])
def list_integration_types():
    return [
        IntegrationTypeRead(**vars(item))
        for item in sorted(INTEGRATION_TYPES.values(), key=lambda value: value.name.lower())
    ]


@router.get("", response_model=list[IntegrationRead])
def list_integrations(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Integration).order_by(Integration.kind, Integration.name)))
    return [_read(row) for row in rows if get_integration_type(row.kind) is not None]


@router.post("", response_model=IntegrationRead)
def upsert_integration(payload: IntegrationUpsert, db: Session = Depends(get_db)):
    kind = payload.kind.strip().lower()
    name = payload.name.strip() or "default"
    integration_type = get_integration_type(kind)

    if integration_type is None:
        allowed = ", ".join(sorted(INTEGRATION_TYPES))
        raise HTTPException(status_code=400, detail=f"unsupported integration kind; expected one of: {allowed}")

    base_url = payload.base_url.strip().rstrip("/")
    if integration_type.requires_base_url and not base_url:
        raise HTTPException(status_code=400, detail=f"{kind} requires base_url")
    if integration_type.requires_access_token and not payload.access_token:
        raise HTTPException(status_code=400, detail=f"{kind} requires access_token")

    row = db.scalar(
        select(Integration).where(
            Integration.kind == kind,
            Integration.name == name,
        )
    )
    if row is None:
        # Legacy upgraded databases can still have a unique constraint on kind.
        existing_kind = db.scalar(select(Integration).where(Integration.kind == kind))
        if existing_kind is not None:
            row = existing_kind
        else:
            row = Integration(kind=kind, name=name, base_url=base_url)
            db.add(row)

    row.name = name
    row.base_url = base_url
    row.access_token = payload.access_token
    row.refresh_token = payload.refresh_token
    row.config_json = json.dumps(payload.config, sort_keys=True)
    row.enabled = payload.enabled
    db.commit()
    db.refresh(row)
    return _read(row)


@router.get("/{kind}/discover", response_model=list[DiscoveredDevice])
async def discover_integration_devices(
    kind: str,
    timeout: float = Query(default=3.0, ge=0.1, le=10.0),
):
    normalized = kind.strip().lower()
    integration_type = get_integration_type(normalized)
    if integration_type is None:
        raise HTTPException(status_code=404, detail="integration type not found")
    if not integration_type.discovery:
        raise HTTPException(status_code=400, detail=f"{normalized} does not support discovery")

    if normalized == "android_tv":
        devices = await discover_android_tv_devices(timeout)
        return [
            DiscoveredDevice(
                source_device_id=item.source_device_id,
                name=item.name,
                host=item.host,
                port=item.port,
                model=item.model,
            )
            for item in devices
        ]

    raise HTTPException(status_code=501, detail=f"{normalized} discovery is not implemented")


@router.post("/{kind}/{name}/test", response_model=IntegrationTestResult)
async def test_saved_integration(kind: str, name: str, db: Session = Depends(get_db)):
    row = db.scalar(
        select(Integration).where(
            Integration.kind == kind.lower(),
            Integration.name == name,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    if row.kind == "android_tv":
        return IntegrationTestResult(
            kind=row.kind,
            name=row.name,
            ok=True,
            server_name=row.name,
            version="remote-v2",
        )

    try:
        if row.kind == TMDB_KIND:
            return await test_tmdb_integration(row)
        if row.kind in ARR_SUPPORTED_KINDS:
            return await test_arr_integration(row)
        raise HTTPException(status_code=400, detail=f"{row.kind} does not support connection testing")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{kind} connection failed: {exc}") from exc

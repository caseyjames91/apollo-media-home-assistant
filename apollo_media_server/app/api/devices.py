import json
import uuid
from datetime import datetime, timezone

from androidtvremote2 import CannotConnect, ConnectionClosed, InvalidAuth
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.device import Device
from app.models.integration import Integration
from app.models.room import Room
from app.schemas.device import (
    AndroidTVPairFinish,
    AndroidTVPairFinishResult,
    AndroidTVPairStartResult,
    AndroidTVState,
    DeviceCommand,
    DeviceControlGroup,
    DeviceControlProfile,
    DeviceImport,
    DeviceLaunch,
    DeviceRead,
    DeviceRegister,
    DeviceUpdate,
)
from app.services import android_tv_control


router = APIRouter(prefix="/devices", tags=["devices"])


ANDROID_TV_CONTROL_GROUPS = {
    "power": ["POWER"],
    "navigation": [
        "DPAD_UP",
        "DPAD_DOWN",
        "DPAD_LEFT",
        "DPAD_RIGHT",
        "DPAD_CENTER",
        "BACK",
        "HOME",
    ],
    "volume": ["VOLUME_UP", "VOLUME_DOWN", "MUTE"],
    "media": [
        "MEDIA_PLAY",
        "MEDIA_PAUSE",
        "MEDIA_PLAY_PAUSE",
        "MEDIA_STOP",
        "MEDIA_PREVIOUS",
        "MEDIA_NEXT",
    ],
}


def _json_object(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _read(row: Device) -> DeviceRead:
    return DeviceRead(
        id=row.id,
        name=row.name,
        device_key=row.device_key,
        device_type=row.device_type,
        ha_entity_id=row.ha_entity_id,
        integration_id=row.integration_id,
        source_device_id=row.source_device_id,
        source_name=row.source_name,
        room_id=row.room_id,
        capabilities=_json_list(row.capabilities_json),
        config=_json_object(row.config_json),
        enabled=row.enabled,
    )


def _integration_for_device(device: Device, db: Session) -> Integration:
    if device.integration_id is None:
        raise HTTPException(status_code=400, detail="device has no integration")
    integration = db.get(Integration, device.integration_id)
    if integration is None:
        raise HTTPException(status_code=400, detail="device integration not found")
    return integration


def _android_tv(device_id: uuid.UUID, db: Session) -> tuple[Device, Integration]:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    integration = _integration_for_device(device, db)
    if integration.kind != "android_tv":
        raise HTTPException(status_code=400, detail="device is not an Android TV device")
    return device, integration


def _legacy_android_tv_match(
    payload: DeviceImport,
    db: Session,
) -> Device | None:
    if not payload.source_device_id.lower().startswith("mac:"):
        return None

    host = str(payload.config.get("host", "")).strip()
    try:
        port = int(payload.config.get("port", 6466))
    except (TypeError, ValueError):
        return None

    if not host:
        return None

    legacy_source_id = f"{host}:{port}"
    candidates = list(
        db.scalars(
            select(Device).where(
                Device.integration_id == payload.integration_id,
                Device.source_device_id == legacy_source_id,
            )
        )
    )

    matches: list[Device] = []
    for candidate in candidates:
        config = _json_object(candidate.config_json)
        candidate_host = str(config.get("host", "")).strip()
        try:
            candidate_port = int(config.get("port", 6466))
        except (TypeError, ValueError):
            continue
        if candidate_host == host and candidate_port == port:
            matches.append(candidate)

    return matches[0] if len(matches) == 1 else None


@router.post("/register", response_model=DeviceRead)
def register_device(payload: DeviceRegister, db: Session = Depends(get_db)):
    row = db.scalar(select(Device).where(Device.device_key == payload.device_key))
    if row is None:
        row = Device(**payload.model_dump())
        db.add(row)
    else:
        row.name = payload.name
        row.device_type = payload.device_type
        row.ha_entity_id = payload.ha_entity_id
        row.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/import", response_model=DeviceRead)
def import_device(payload: DeviceImport, db: Session = Depends(get_db)):
    integration = db.get(Integration, payload.integration_id)
    if integration is None:
        raise HTTPException(status_code=400, detail="integration not found")

    if payload.room_id is not None and db.get(Room, payload.room_id) is None:
        raise HTTPException(status_code=400, detail="room not found")

    row = db.scalar(
        select(Device).where(
            Device.integration_id == payload.integration_id,
            Device.source_device_id == payload.source_device_id,
        )
    )

    migrated_legacy_android_tv = False
    if row is None and integration.kind == "android_tv":
        row = _legacy_android_tv_match(payload, db)
        migrated_legacy_android_tv = row is not None

    stable_key = f"{integration.kind}:{payload.integration_id}:{payload.source_device_id}"
    if row is None:
        row = Device(
            name=payload.name,
            device_key=stable_key,
            device_type=payload.device_type,
        )
        db.add(row)

    row.device_key = stable_key
    row.integration_id = payload.integration_id
    row.source_device_id = payload.source_device_id
    row.source_name = payload.source_name or payload.name
    row.device_type = payload.device_type
    row.capabilities_json = json.dumps(payload.capabilities, sort_keys=True)
    row.config_json = json.dumps(payload.config, sort_keys=True)
    row.enabled = payload.enabled
    row.last_seen_at = datetime.now(timezone.utc)

    if not migrated_legacy_android_tv:
        row.name = payload.name
        row.room_id = payload.room_id

    db.commit()
    db.refresh(row)
    return _read(row)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: uuid.UUID,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
):
    row = db.get(Device, device_id)
    if row is None:
        raise HTTPException(status_code=404, detail="device not found")

    changes = payload.model_dump(exclude_unset=True)
    if "room_id" in changes and changes["room_id"] is not None:
        if db.get(Room, changes["room_id"]) is None:
            raise HTTPException(status_code=400, detail="room not found")

    if "config" in changes:
        row.config_json = json.dumps(changes.pop("config") or {}, sort_keys=True)

    for key, value in changes.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return _read(row)


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Device).order_by(Device.name)))
    return [_read(row) for row in rows]


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    if device.integration_id is not None:
        integration = db.get(Integration, device.integration_id)
        if integration is not None and integration.kind == "android_tv":
            android_tv_control.close_device_connection(device.id)

    db.delete(device)
    db.commit()
    return None


@router.get("/{device_id}/controls", response_model=DeviceControlProfile)
def get_device_controls(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    integration = _integration_for_device(device, db)
    capabilities = _json_list(device.capabilities_json)

    groups: list[DeviceControlGroup] = []
    launch_supported = False
    state_supported = False

    if integration.kind == "android_tv":
        groups = [
            DeviceControlGroup(
                capability=capability,
                commands=commands,
            )
            for capability, commands in ANDROID_TV_CONTROL_GROUPS.items()
            if capability in capabilities
        ]
        launch_supported = "launch_app" in capabilities
        state_supported = True

    return DeviceControlProfile(
        device_id=device.id,
        integration_kind=integration.kind,
        capabilities=capabilities,
        control_groups=groups,
        launch_supported=launch_supported,
        state_supported=state_supported,
    )


@router.post("/{device_id}/pair/start", response_model=AndroidTVPairStartResult)
async def start_pairing(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device, integration = _android_tv(device_id, db)
    try:
        await android_tv_control.start_pairing(integration, device)
    except (CannotConnect, ConnectionClosed) as exc:
        raise HTTPException(status_code=502, detail=f"could not start Android TV pairing: {exc}") from exc

    return AndroidTVPairStartResult(
        device_id=device.id,
        pairing_started=True,
        message="Enter the pairing code shown on the TV.",
    )


@router.post("/{device_id}/pair/finish", response_model=AndroidTVPairFinishResult)
async def finish_pairing(
    device_id: uuid.UUID,
    payload: AndroidTVPairFinish,
    db: Session = Depends(get_db),
):
    device, _integration = _android_tv(device_id, db)
    try:
        await android_tv_control.finish_pairing(device, payload.code)
    except InvalidAuth as exc:
        raise HTTPException(status_code=400, detail="invalid Android TV pairing code") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(device)
    return AndroidTVPairFinishResult(device_id=device.id, paired=True)


@router.get("/{device_id}/state", response_model=AndroidTVState)
async def get_device_state(device_id: uuid.UUID, db: Session = Depends(get_db)):
    device, integration = _android_tv(device_id, db)
    try:
        state = await android_tv_control.get_state(integration, device)
    except InvalidAuth as exc:
        raise HTTPException(status_code=401, detail="Android TV device is not paired") from exc

    return AndroidTVState(device_id=device.id, **state)


@router.post("/{device_id}/command", status_code=204)
async def send_device_command(
    device_id: uuid.UUID,
    payload: DeviceCommand,
    db: Session = Depends(get_db),
):
    device, integration = _android_tv(device_id, db)
    try:
        await android_tv_control.send_key(integration, device, payload.command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidAuth as exc:
        raise HTTPException(status_code=401, detail="Android TV device is not paired") from exc
    except (CannotConnect, ConnectionClosed) as exc:
        raise HTTPException(status_code=502, detail=f"Android TV connection failed: {exc}") from exc
    return None


@router.post("/{device_id}/launch", status_code=204)
async def launch_on_device(
    device_id: uuid.UUID,
    payload: DeviceLaunch,
    db: Session = Depends(get_db),
):
    device, integration = _android_tv(device_id, db)
    try:
        await android_tv_control.launch(integration, device, payload.target)
    except InvalidAuth as exc:
        raise HTTPException(status_code=401, detail="Android TV device is not paired") from exc
    except (CannotConnect, ConnectionClosed) as exc:
        raise HTTPException(status_code=502, detail=f"Android TV connection failed: {exc}") from exc
    return None

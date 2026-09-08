from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP_VERSION = os.environ.get("APOLLO_IR_VERSION", "dev")
HA_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core").rstrip("/")
HA_TOKEN = os.environ.get("HOME_ASSISTANT_TOKEN", "")
API_KEY = os.environ.get("APOLLO_IR_API_KEY", "")
REGISTRY_PATH = Path("/config/devices.json")
HA_STORAGE_PATH = Path("/homeassistant/.storage")

app = FastAPI(title="Apollo IR Server", version=APP_VERSION)
jobs: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_api_key(x_apollo_ir_key: str | None) -> None:
    if API_KEY and x_apollo_ir_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Apollo IR API key")


def ha_headers() -> dict[str, str]:
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="Supervisor token is unavailable")
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"devices": {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {"devices": {}}
    if not isinstance(data, dict) or not isinstance(data.get("devices"), dict):
        return {"devices": {}}
    return data


def save_registry(data: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(REGISTRY_PATH)


def register_device(device: str, display_name: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    devices = registry["devices"]
    entry = devices.setdefault(
        device,
        {
            "id": device,
            "name": display_name or device,
            "commands": {},
            "room": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        },
    )
    if display_name:
        entry["name"] = display_name
    entry.setdefault("room", None)
    entry["updated_at"] = now_iso()
    save_registry(registry)
    return entry


def register_command(
    device: str,
    command: str,
    command_type: str,
    learner_entity_id: str,
) -> None:
    registry = load_registry()
    devices = registry["devices"]
    entry = devices.setdefault(
        device,
        {
            "id": device,
            "name": device,
            "commands": {},
            "room": None,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        },
    )
    entry.setdefault("commands", {})[command] = {
        "name": command,
        "type": command_type,
        "learner_entity_id": learner_entity_id,
        "learned_at": now_iso(),
        "last_used_at": None,
    }
    entry["updated_at"] = now_iso()
    save_registry(registry)


def _looks_like_broadlink_ir(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < 8:
        return False
    try:
        raw = base64.b64decode(value.strip(), validate=True)
    except Exception:
        return False
    return len(raw) >= 6 and raw[0] == 0x26


def _find_raw_code_in_object(
    obj: Any,
    device: str,
    command: str,
) -> str | None:
    if isinstance(obj, dict):
        direct_device = obj.get(device)
        if isinstance(direct_device, dict):
            value = direct_device.get(command)
            if _looks_like_broadlink_ir(value):
                return value.strip()

        if obj.get("device") == device:
            commands = obj.get("commands")
            if isinstance(commands, dict):
                value = commands.get(command)
                if _looks_like_broadlink_ir(value):
                    return value.strip()

        for value in obj.values():
            found = _find_raw_code_in_object(value, device, command)
            if found:
                return found

    elif isinstance(obj, list):
        for value in obj:
            found = _find_raw_code_in_object(value, device, command)
            if found:
                return found

    return None


def find_broadlink_raw_code(device: str, command: str) -> tuple[str, str]:
    if not HA_STORAGE_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Home Assistant storage is not mounted in Apollo IR Server",
        )

    candidates = sorted(
        path for path in HA_STORAGE_PATH.iterdir()
        if path.is_file() and "broadlink" in path.name.lower()
    )

    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue

        found = _find_raw_code_in_object(data, device, command)
        if found:
            return found, path.name

    raise HTTPException(
        status_code=404,
        detail=f"No raw BroadLink IR code found for {device} / {command}",
    )


class LearnRequest(BaseModel):
    learner_entity_id: str
    device: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=128)
    command_type: str = "ir"
    timeout: int = Field(default=30, ge=5, le=120)


class SendRequest(BaseModel):
    remote_entity_id: str
    device: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=128)


class DeviceRequest(BaseModel):
    device: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=128)


class CommandDeleteRequest(BaseModel):
    remote_entity_id: str
    device: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=128)


class DeviceDeleteRequest(BaseModel):
    remote_entity_id: str | None = None
    device: str = Field(min_length=1, max_length=128)
    delete_commands: bool = False


class DeviceRoomRequest(BaseModel):
    device: str = Field(min_length=1, max_length=128)
    room: str | None = Field(default=None, max_length=128)


async def run_learning_job(job_id: str, req: LearnRequest) -> None:
    job = jobs[job_id]
    job["state"] = "waiting_for_signal"
    job["message"] = (
        "Hold/press the original RF remote button as instructed by BroadLink."
        if req.command_type == "rf"
        else "Point the original remote at the BroadLink and press the button."
    )
    job["updated_at"] = now_iso()

    payload = {
        "entity_id": req.learner_entity_id,
        "device": req.device,
        "command": req.command,
        "command_type": req.command_type,
        "timeout": req.timeout,
    }

    try:
        async with httpx.AsyncClient(timeout=req.timeout + 15.0) as client:
            response = await client.post(
                f"{HA_URL}/api/services/remote/learn_command",
                headers=ha_headers(),
                json=payload,
            )
        response.raise_for_status()
    except asyncio.CancelledError:
        job["state"] = "cancelled"
        job["message"] = "Learning cancelled."
        job["updated_at"] = now_iso()
        raise
    except Exception as err:
        text = str(err)
        low = text.lower()
        job["state"] = "timeout" if "timeout" in low else "error"
        job["message"] = (
            "No command was learned before the timeout."
            if job["state"] == "timeout"
            else "Home Assistant could not learn the command."
        )
        job["error"] = text
        job["updated_at"] = now_iso()
        return

    register_command(
        req.device,
        req.command,
        req.command_type,
        req.learner_entity_id,
    )
    job["state"] = "learned"
    job["message"] = f"{req.device} / {req.command} learned successfully."
    job["updated_at"] = now_iso()


@app.get("/status")
async def status(x_apollo_ir_key: str | None = Header(default=None)) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    return {
        "ok": True,
        "service": "apollo_ir_server",
        "version": APP_VERSION,
        "ha_backend": True,
        "device_registry": True,
        "raw_code_import": True,
    }


@app.get("/api/learners")
async def learners(x_apollo_ir_key: str | None = Header(default=None)) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{HA_URL}/api/states", headers=ha_headers())
    response.raise_for_status()

    result = []
    for state in response.json():
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith("remote."):
            continue
        attrs = state.get("attributes") or {}
        result.append(
            {
                "entity_id": entity_id,
                "name": attrs.get("friendly_name", entity_id),
                "state": state.get("state"),
            }
        )

    result.sort(key=lambda item: str(item["name"]).lower())
    return {"learners": result}


@app.get("/api/devices")
async def devices(x_apollo_ir_key: str | None = Header(default=None)) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    registry = load_registry()
    result = list(registry["devices"].values())
    result.sort(key=lambda item: str(item.get("name", item.get("id", ""))).lower())
    return {"devices": result}


@app.post("/api/devices")
async def add_device(
    req: DeviceRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    entry = register_device(req.device.strip(), (req.name or "").strip() or None)
    return {"ok": True, "device": entry}


@app.post("/api/learn", status_code=202)
async def learn(
    req: LearnRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    if req.command_type not in {"ir", "rf"}:
        raise HTTPException(status_code=400, detail="command_type must be ir or rf")
    if not req.learner_entity_id.startswith("remote."):
        raise HTTPException(status_code=400, detail="learner_entity_id must be remote.*")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{HA_URL}/api/states/{req.learner_entity_id}",
            headers=ha_headers(),
        )
    if response.status_code == 404:
        raise HTTPException(status_code=400, detail="Unknown learner entity")
    response.raise_for_status()

    register_device(req.device)

    job_id = uuid.uuid4().hex
    created = now_iso()
    jobs[job_id] = {
        "id": job_id,
        "learner_entity_id": req.learner_entity_id,
        "device": req.device,
        "command": req.command,
        "command_type": req.command_type,
        "timeout": req.timeout,
        "state": "starting",
        "message": "Starting learning through Home Assistant…",
        "created_at": created,
        "updated_at": created,
        "error": None,
    }
    asyncio.create_task(run_learning_job(job_id, req))
    return jobs[job_id]


@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Learning job not found")
    return jobs[job_id]


@app.get("/api/raw-code")
async def raw_code(
    device: str,
    command: str,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    device = device.strip()
    command = command.strip()

    if not device or not command:
        raise HTTPException(status_code=400, detail="device and command are required")

    code, source = find_broadlink_raw_code(device, command)

    return {
        "ok": True,
        "device": device,
        "command": command,
        "format": "broadlink_base64",
        "carrier_hz": 38000,
        "code": code,
        "source": source,
    }


@app.post("/api/send")
async def send_command(
    req: SendRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    if not req.remote_entity_id.startswith("remote."):
        raise HTTPException(status_code=400, detail="remote_entity_id must be remote.*")

    payload = {
        "entity_id": req.remote_entity_id,
        "device": req.device,
        "command": req.command,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{HA_URL}/api/services/remote/send_command",
            headers=ha_headers(),
            json=payload,
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant send failed: {response.status_code} {response.text}",
        )

    registry = load_registry()
    device_entry = registry["devices"].get(req.device)
    if device_entry:
        command_entry = (device_entry.get("commands") or {}).get(req.command)
        if command_entry:
            command_entry["last_used_at"] = now_iso()
            device_entry["updated_at"] = now_iso()
            save_registry(registry)

    return {
        "ok": True,
        "remote_entity_id": req.remote_entity_id,
        "device": req.device,
        "command": req.command,
    }


@app.post("/api/commands/delete")
async def delete_command(
    req: CommandDeleteRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    if not req.remote_entity_id.startswith("remote."):
        raise HTTPException(status_code=400, detail="remote_entity_id must be remote.*")

    payload = {
        "entity_id": req.remote_entity_id,
        "device": req.device,
        "command": req.command,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{HA_URL}/api/services/remote/delete_command",
            headers=ha_headers(),
            json=payload,
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant delete failed: {response.status_code} {response.text}",
        )

    registry = load_registry()
    device_entry = registry["devices"].get(req.device)
    if device_entry:
        commands = device_entry.get("commands") or {}
        commands.pop(req.command, None)
        device_entry["commands"] = commands
        device_entry["updated_at"] = now_iso()
        save_registry(registry)

    return {"ok": True, "device": req.device, "command": req.command}


@app.post("/api/devices/delete")
async def delete_device(
    req: DeviceDeleteRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    registry = load_registry()
    device_entry = registry["devices"].get(req.device)
    if not device_entry:
        raise HTTPException(status_code=404, detail="Device not found")

    commands = list((device_entry.get("commands") or {}).keys())

    if commands and not req.delete_commands:
        raise HTTPException(
            status_code=409,
            detail="Device still has commands. Set delete_commands=true to remove them first.",
        )

    if commands:
        if not req.remote_entity_id or not req.remote_entity_id.startswith("remote."):
            raise HTTPException(
                status_code=400,
                detail="remote_entity_id is required when deleting a device with commands",
            )

        payload = {
            "entity_id": req.remote_entity_id,
            "device": req.device,
            "command": commands,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{HA_URL}/api/services/remote/delete_command",
                headers=ha_headers(),
                json=payload,
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Home Assistant device cleanup failed: {response.status_code} {response.text}",
            )

    registry["devices"].pop(req.device, None)
    save_registry(registry)

    return {"ok": True, "device": req.device, "deleted_commands": commands}


@app.post("/api/devices/room")
async def set_device_room(
    req: DeviceRoomRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    registry = load_registry()
    device_entry = registry["devices"].get(req.device)
    if not device_entry:
        raise HTTPException(status_code=404, detail="Device not found")

    room = (req.room or "").strip() or None
    device_entry["room"] = room
    device_entry["updated_at"] = now_iso()
    save_registry(registry)

    return {"ok": True, "device": req.device, "room": room}

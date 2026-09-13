import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from androidtvremote2 import (
    AndroidTVRemote,
    CannotConnect,
    ConnectionClosed,
    InvalidAuth,
)

from app.core.config import settings
from app.models.device import Device
from app.models.integration import Integration


CLIENT_NAME = "Apollo Media Server"

KEY_COMMANDS = {
    "BACK",
    "DPAD_CENTER",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",
    "DPAD_UP",
    "HOME",
    "MEDIA_NEXT",
    "MEDIA_PAUSE",
    "MEDIA_PLAY",
    "MEDIA_PLAY_PAUSE",
    "MEDIA_PREVIOUS",
    "MEDIA_STOP",
    "MUTE",
    "POWER",
    "VOLUME_DOWN",
    "VOLUME_UP",
}


@dataclass
class PairingSession:
    remote: AndroidTVRemote
    device_id: uuid.UUID


_pairing_sessions: dict[uuid.UUID, PairingSession] = {}


def _device_config(device: Device) -> dict:
    try:
        value = json.loads(device.config_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_device_config(device: Device, config: dict) -> None:
    device.config_json = json.dumps(config, sort_keys=True)


def _credentials(integration: Integration) -> tuple[Path, Path]:
    root = Path(settings.data_dir) / "android_tv" / str(integration.id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "cert.pem", root / "key.pem"


def _host(device: Device) -> str:
    config = _device_config(device)
    host = str(config.get("host", "")).strip()
    if not host:
        raise ValueError("Android TV device is missing host")
    return host


def _remote(integration: Integration, device: Device) -> AndroidTVRemote:
    certfile, keyfile = _credentials(integration)
    return AndroidTVRemote(
        CLIENT_NAME,
        str(certfile),
        str(keyfile),
        _host(device),
    )


async def start_pairing(integration: Integration, device: Device) -> None:
    existing = _pairing_sessions.pop(device.id, None)
    if existing is not None:
        existing.remote.disconnect()

    remote = _remote(integration, device)
    await remote.async_generate_cert_if_missing()
    await remote.async_start_pairing()
    _pairing_sessions[device.id] = PairingSession(remote=remote, device_id=device.id)


async def finish_pairing(device: Device, code: str) -> None:
    session = _pairing_sessions.get(device.id)
    if session is None:
        raise RuntimeError("pairing has not been started")

    try:
        await session.remote.async_finish_pairing(code.strip())
    except InvalidAuth:
        # Keep the session alive so the user can retry the displayed PIN.
        raise
    else:
        session.remote.disconnect()
        _pairing_sessions.pop(device.id, None)
        config = _device_config(device)
        config["paired"] = True
        _write_device_config(device, config)


async def _connect(integration: Integration, device: Device) -> AndroidTVRemote:
    remote = _remote(integration, device)
    await remote.async_connect()
    return remote


async def get_state(integration: Integration, device: Device) -> dict:
    remote = _remote(integration, device)
    try:
        await remote.async_connect()
        await asyncio.sleep(0.1)
        return {
            "available": True,
            "is_on": remote.is_on,
            "current_app": remote.current_app or None,
            "volume": remote.volume_info or None,
            "device_info": remote.device_info or None,
        }
    except (CannotConnect, ConnectionClosed):
        return {
            "available": False,
            "is_on": None,
            "current_app": None,
            "volume": None,
            "device_info": None,
        }
    finally:
        remote.disconnect()


async def send_key(integration: Integration, device: Device, command: str) -> None:
    normalized = command.strip().upper()
    if normalized not in KEY_COMMANDS:
        raise ValueError(f"unsupported Android TV command: {normalized}")

    remote = await _connect(integration, device)
    try:
        remote.send_key_command(normalized)
        await asyncio.sleep(0.05)
    finally:
        remote.disconnect()


async def launch(integration: Integration, device: Device, target: str) -> None:
    remote = await _connect(integration, device)
    try:
        remote.send_launch_app_command(target.strip())
        await asyncio.sleep(0.05)
    finally:
        remote.disconnect()

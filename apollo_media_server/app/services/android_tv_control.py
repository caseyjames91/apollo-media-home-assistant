import asyncio
import json
import uuid
from dataclasses import dataclass, field
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


@dataclass
class DeviceConnection:
    remote: AndroidTVRemote
    host: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connected: bool = False


_pairing_sessions: dict[uuid.UUID, PairingSession] = {}
_connections: dict[uuid.UUID, DeviceConnection] = {}


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


def _get_connection(integration: Integration, device: Device) -> DeviceConnection:
    host = _host(device)
    connection = _connections.get(device.id)

    # Recreate the client if the device was reconfigured to a different host.
    if connection is not None and connection.host != host:
        connection.remote.disconnect()
        _connections.pop(device.id, None)
        connection = None

    if connection is None:
        connection = DeviceConnection(
            remote=_remote(integration, device),
            host=host,
        )
        _connections[device.id] = connection

    return connection


async def _connect_locked(connection: DeviceConnection) -> None:
    if connection.connected:
        return

    await connection.remote.async_connect()

    # Remote v2 needs a brief initial settle period before the first
    # command is reliably accepted. This only happens on a fresh
    # connection; subsequent commands reuse the live connection.
    await asyncio.sleep(0.5)

    connection.connected = True


def _mark_disconnected(connection: DeviceConnection) -> None:
    connection.connected = False
    connection.remote.disconnect()


async def start_pairing(integration: Integration, device: Device) -> None:
    existing = _pairing_sessions.pop(device.id, None)
    if existing is not None:
        existing.remote.disconnect()

    existing_connection = _connections.pop(device.id, None)
    if existing_connection is not None:
        existing_connection.remote.disconnect()

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


async def get_state(integration: Integration, device: Device) -> dict:
    connection = _get_connection(integration, device)

    async with connection.lock:
        try:
            first_connect = not connection.connected
            await _connect_locked(connection)
            if first_connect:
                # Initial state arrives asynchronously after the Remote v2
                # connection is established.
                await asyncio.sleep(0.1)

            remote = connection.remote
            return {
                "available": True,
                "is_on": remote.is_on,
                "current_app": remote.current_app or None,
                "volume": remote.volume_info or None,
                "device_info": remote.device_info or None,
            }
        except (CannotConnect, ConnectionClosed):
            _mark_disconnected(connection)
            return {
                "available": False,
                "is_on": None,
                "current_app": None,
                "volume": None,
                "device_info": None,
            }


async def send_key(integration: Integration, device: Device, command: str) -> None:
    normalized = command.strip().upper()
    if normalized not in KEY_COMMANDS:
        raise ValueError(f"unsupported Android TV command: {normalized}")

    connection = _get_connection(integration, device)

    async with connection.lock:
        try:
            await _connect_locked(connection)
            connection.remote.send_key_command(normalized)
        except (CannotConnect, ConnectionClosed):
            # Drop the stale session and retry once on a fresh connection.
            _mark_disconnected(connection)
            await _connect_locked(connection)
            connection.remote.send_key_command(normalized)


async def launch(integration: Integration, device: Device, target: str) -> None:
    target = target.strip()
    if not target:
        raise ValueError("Android TV launch target is required")

    connection = _get_connection(integration, device)

    async with connection.lock:
        try:
            await _connect_locked(connection)
            connection.remote.send_launch_app_command(target)
            # androidtvremote2 buffers app-link launches and writes them
            # asynchronously. Give the event loop a brief opportunity to
            # flush the queued Remote v2 message before returning to the API.
            await asyncio.sleep(0.1)
        except (CannotConnect, ConnectionClosed):
            _mark_disconnected(connection)
            await _connect_locked(connection)
            connection.remote.send_launch_app_command(target)
            await asyncio.sleep(0.1)


def close_device_connection(device_id: uuid.UUID) -> None:
    connection = _connections.pop(device_id, None)
    if connection is not None:
        connection.remote.disconnect()
        connection.connected = False

    session = _pairing_sessions.pop(device_id, None)
    if session is not None:
        session.remote.disconnect()


def close_all_connections() -> None:
    for device_id in list(_connections):
        close_device_connection(device_id)

    for device_id in list(_pairing_sessions):
        close_device_connection(device_id)

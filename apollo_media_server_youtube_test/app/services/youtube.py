from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.device import Device
from app.services import kodi
import asyncio
import json
from pathlib import Path

BRIDGE = Path("/opt/apollo/youtube_bridge/bridge.mjs")


async def _run(command: str) -> dict:
    process = await asyncio.create_subprocess_exec(
        "node",
        str(BRIDGE),
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"YouTube bridge exited {process.returncode}")

    try:
        return json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("YouTube bridge returned invalid JSON") from exc


async def status() -> dict:
    return await _run("status")


async def home() -> dict:
    return await _run("home")


async def history() -> dict:
    return await _run("history")

async def continue_watching() -> dict:
    data = await history()
    items = []

    for item in data.get("items", []):
        start_seconds = item.get("start_seconds")
        progress = item.get("progress_percent")

        if not isinstance(start_seconds, (int, float)) or start_seconds <= 0:
            continue
        if isinstance(progress, (int, float)) and progress >= 95:
            continue

        items.append(item)

    return {
        "kind": "continue_watching",
        "count": len(items),
        "items": items,
    }

async def play(
    db: Session,
    device_key: str,
    video_id: str,
    start_seconds: float | None = None,
) -> dict:
    device = db.scalar(select(Device).where(Device.device_key == device_key))
    if device is None:
        raise RuntimeError(f"Unknown device: {device_key}")
    if not device.kodi_jsonrpc_url:
        raise RuntimeError(f"Device has no Kodi JSON-RPC URL: {device_key}")

    plugin_url = f"plugin://plugin.video.youtube/play/?video_id={video_id}"

    await kodi.open_file(
        device.kodi_jsonrpc_url,
        plugin_url,
    )

    if start_seconds and start_seconds > 0:
        await asyncio.sleep(2)
        await kodi.seek(
            device.kodi_jsonrpc_url,
            1,
            float(start_seconds),
        )

    return {
        "device_key": device_key,
        "ha_entity_id": device.ha_entity_id,
        "kodi_jsonrpc_url": device.kodi_jsonrpc_url,
        "video_id": video_id,
        "start_seconds": start_seconds or 0,
        "playback_url": plugin_url,
    }

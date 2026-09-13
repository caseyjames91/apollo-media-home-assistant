import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from androidtvremote2 import AndroidTVRemote
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from app.core.config import settings


SERVICE_TYPE = "_androidtvremote2._tcp.local."
CLIENT_NAME = "Apollo Media Server"
IDENTITY_TIMEOUT_SECONDS = 2.5

LOGGER = logging.getLogger(__name__)

_MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$")


@dataclass(frozen=True)
class AndroidTVDiscoveredDevice:
    source_device_id: str
    name: str
    host: str
    port: int
    model: str | None = None
    mac: str | None = None
    certificate_name: str | None = None
    stable_identity: bool = False


def _decode_property(properties: dict[bytes, bytes | None], key: bytes) -> str | None:
    value = properties.get(key)
    if value is None:
        return None
    return value.decode("utf-8", errors="replace").strip() or None


def normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().replace("-", ":").upper()
    if not _MAC_RE.fullmatch(candidate):
        return None
    return candidate


def android_tv_source_id(mac: str) -> str:
    normalized = normalize_mac(mac)
    if normalized is None:
        raise ValueError("invalid Android TV MAC address")
    return f"mac:{normalized.lower()}"


def _identity_credentials() -> tuple[Path, Path]:
    root = Path(settings.data_dir) / "android_tv" / "discovery"
    root.mkdir(parents=True, exist_ok=True)
    return root / "cert.pem", root / "key.pem"


async def _ensure_identity_credentials() -> tuple[Path, Path]:
    certfile, keyfile = _identity_credentials()
    remote = AndroidTVRemote(
        CLIENT_NAME,
        str(certfile),
        str(keyfile),
        "127.0.0.1",
    )
    await remote.async_generate_cert_if_missing()
    return certfile, keyfile


async def _certificate_identity(
    host: str,
    certfile: Path,
    keyfile: Path,
) -> tuple[str | None, str | None]:
    remote = AndroidTVRemote(
        CLIENT_NAME,
        str(certfile),
        str(keyfile),
        host,
    )
    try:
        certificate_name, raw_mac = await asyncio.wait_for(
            remote.async_get_name_and_mac(),
            timeout=IDENTITY_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        LOGGER.debug("Unable to read Android TV certificate identity for %s: %s", host, exc)
        return None, None
    finally:
        remote.disconnect()

    return (certificate_name.strip() or None, normalize_mac(raw_mac))


async def discover_android_tv_devices(timeout: float = 3.0) -> list[AndroidTVDiscoveredDevice]:
    found: dict[str, AndroidTVDiscoveredDevice] = {}
    tasks: set[asyncio.Task] = set()

    certfile, keyfile = await _ensure_identity_credentials()
    zc = AsyncZeroconf()

    async def resolve(service_type: str, service_name: str) -> None:
        info = AsyncServiceInfo(service_type, service_name)
        if not await info.async_request(zc.zeroconf, 2500):
            return

        addresses = info.parsed_scoped_addresses()
        if not addresses:
            return

        properties = info.properties or {}
        friendly_name = _decode_property(properties, b"fn")
        model = _decode_property(properties, b"md")
        host = addresses[0]
        clean_service_name = service_name.removesuffix(f".{SERVICE_TYPE}").rstrip(".")
        name = friendly_name or clean_service_name or host

        certificate_name, mac = await _certificate_identity(host, certfile, keyfile)

        if mac is not None:
            source_id = android_tv_source_id(mac)
            stable_identity = True
        else:
            source_id = f"{host}:{info.port}"
            stable_identity = False

        found[source_id] = AndroidTVDiscoveredDevice(
            source_device_id=source_id,
            name=name,
            host=host,
            port=int(info.port),
            model=model,
            mac=mac,
            certificate_name=certificate_name,
            stable_identity=stable_identity,
        )

    def on_state_change(zeroconf, service_type, name, state_change) -> None:
        if state_change is not ServiceStateChange.Added:
            return
        task = asyncio.create_task(resolve(service_type, name))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    browser = AsyncServiceBrowser(
        zc.zeroconf,
        [SERVICE_TYPE],
        handlers=[on_state_change],
    )

    try:
        await asyncio.sleep(max(0.1, min(timeout, 10.0)))
        if tasks:
            await asyncio.gather(*list(tasks), return_exceptions=True)
    finally:
        await browser.async_cancel()
        await zc.async_close()

    return sorted(found.values(), key=lambda item: (item.name.lower(), item.host))

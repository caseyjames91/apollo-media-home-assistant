import asyncio
from dataclasses import dataclass

from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf


SERVICE_TYPE = "_androidtvremote2._tcp.local."


@dataclass(frozen=True)
class AndroidTVDiscoveredDevice:
    source_device_id: str
    name: str
    host: str
    port: int
    model: str | None = None


def _decode_property(properties: dict[bytes, bytes | None], key: bytes) -> str | None:
    value = properties.get(key)
    if value is None:
        return None
    return value.decode("utf-8", errors="replace").strip() or None


async def discover_android_tv_devices(timeout: float = 3.0) -> list[AndroidTVDiscoveredDevice]:
    found: dict[str, AndroidTVDiscoveredDevice] = {}
    tasks: set[asyncio.Task] = set()

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

        source_id = f"{host}:{info.port}"
        found[source_id] = AndroidTVDiscoveredDevice(
            source_device_id=source_id,
            name=name,
            host=host,
            port=int(info.port),
            model=model,
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

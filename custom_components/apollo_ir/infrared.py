"""Home Assistant infrared emitter backed by Apollo AVA IR Bridge."""

from __future__ import annotations

from typing import Any

from homeassistant.components.infrared import InfraredEmitterEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PORT, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the AVA infrared emitter entity."""
    async_add_entities([ApolloAvaInfraredEmitter(entry)])


class ApolloAvaInfraredEmitter(InfraredEmitterEntity):
    """AVA remote infrared emitter."""

    _attr_has_entity_name = True
    _attr_name = "IR emitter"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._attr_unique_id = f"{entry.unique_id}_infrared"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer="Apollo",
            model="AVA IR Bridge",
        )

    async def async_send_command(self, command: Any) -> None:
        """Send an IR command through the AVA bridge."""
        timings = [
            int(interval)
            for timing in command.get_raw_timings()
            for interval in (timing.high_us, timing.low_us)
            if int(interval) > 0
        ]

        if len(timings) < 2:
            raise HomeAssistantError("IR command produced no usable raw timings")

        modulation = int(command.modulation or 38000)
        session = async_get_clientsession(self.hass)

        try:
            async with session.post(
                f"http://{self._host}:{self._port}/ir/raw",
                json={
                    "modulation_hz": modulation,
                    "timings_us": timings,
                },
                timeout=5,
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400 or not payload.get("ok"):
                    raise HomeAssistantError(
                        f"AVA IR Bridge rejected command: {payload}"
                    )
        except HomeAssistantError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Unable to send command through AVA IR Bridge: {err}"
            ) from err

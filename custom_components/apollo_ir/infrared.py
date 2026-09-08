"""Native Home Assistant infrared emitter backed by AVA IR Bridge.

This platform is intentionally scaffolded first. The AVA bridge currently
accepts BroadLink packets at /ir/broadlink. The next bridge revision adds
/raw transmission so this entity can transmit Home Assistant's protocol-
agnostic raw timings without BroadLink-specific coupling.
"""

from __future__ import annotations

from homeassistant.components.infrared import InfraredEmitterEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_PORT


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
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._attr_unique_id = f"{entry.unique_id}_infrared"
        self._attr_device_info = {
            "identifiers": {("apollo_ir", entry.entry_id)},
            "name": entry.data[CONF_NAME],
            "manufacturer": "Apollo",
            "model": "AVA IR Bridge",
        }

    async def async_send_command(self, command) -> None:
        """Send a native HA infrared command.

        Implemented in the next bridge checkpoint together with POST /ir/raw.
        """
        raise NotImplementedError(
            "Native raw IR transmission requires AVA IR Bridge /ir/raw support"
        )

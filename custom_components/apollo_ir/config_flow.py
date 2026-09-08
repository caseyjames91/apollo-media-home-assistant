"""Config flow for Apollo IR."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PORT, DEFAULT_PORT, DOMAIN


class ApolloIrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure an AVA IR Bridge."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle initial setup."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            session = async_get_clientsession(self.hass)

            try:
                async with session.get(
                    f"http://{host}:{port}/status",
                    timeout=5,
                ) as response:
                    response.raise_for_status()
                    status = await response.json()
                if not status.get("emitter"):
                    errors["base"] = "no_ir_emitter"
                else:
                    await self.async_set_unique_id(f"{host}:{port}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )
            except Exception:  # noqa: BLE001 - converted to config-flow error
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="AVA IR Bridge"): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

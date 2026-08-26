"""Config flow for AISFriends."""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEBUG,
    CONF_MMSI_LIST,
    CONF_RATE_MINUTES,
    CONF_USERNAME,
    DEFAULT_RATE_MINUTES,
    DOMAIN,
    MAX_RATE_MINUTES,
    MIN_RATE_MINUTES,
)

_LOGGER = logging.getLogger(__name__)
API_BASE = "https://www.aisfriends.com/api/public/v1"


def _parse_mmsi_input(raw: str) -> list[str]:
    """Parse and de-duplicate 9-digit MMSI values."""
    result: list[str] = []
    for part in re.split(r"[,\n\r;]+", raw):
        value = part.strip()
        if re.fullmatch(r"\d{9}", value) and value not in result:
            result.append(value)
    return result


async def _validate_credentials(
    hass: HomeAssistant, token: str, mmsi_list: list[str]
) -> str | None:
    """Validate the token against one configured MMSI."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"{API_BASE}/vessels/latest-position",
            params={"mmsi": mmsi_list[0]},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status in (401, 403):
                return "invalid_auth"
            if response.status == 429:
                return "rate_limited"
            if response.status >= 500:
                return "cannot_connect"
            if response.status in (200, 404):
                return None
            _LOGGER.debug("Unexpected AISFriends validation status: %s", response.status)
            return "cannot_connect"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"


def _schema(
    *,
    token: str | None = None,
    mmsi: str = "",
    rate: int = DEFAULT_RATE_MINUTES,
    debug: bool = False,
    include_token: bool = True,
) -> vol.Schema:
    """Build a config or options schema."""
    fields: dict[Any, Any] = {}
    if include_token:
        fields[vol.Required(CONF_USERNAME, default=token or "")] = str
    fields[vol.Required(CONF_MMSI_LIST, default=mmsi)] = str
    fields[vol.Required(CONF_RATE_MINUTES, default=rate)] = vol.All(
        int, vol.Range(min=MIN_RATE_MINUTES, max=MAX_RATE_MINUTES)
    )
    fields[vol.Optional(CONF_DEBUG, default=debug)] = bool
    return vol.Schema(fields)


class AISFriendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an AISFriends config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle setup from the integrations UI."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_USERNAME].strip()
            mmsi_list = _parse_mmsi_input(user_input[CONF_MMSI_LIST])
            if not mmsi_list:
                errors[CONF_MMSI_LIST] = "no_mmsi"
            else:
                error = await _validate_credentials(self.hass, token, mmsi_list)
                if error:
                    errors["base"] = error
                else:
                    token_id = hashlib.sha256(token.encode()).hexdigest()
                    await self.async_set_unique_id(token_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="AISFriends Vessel Tracker",
                        data={
                            CONF_USERNAME: token,
                            CONF_MMSI_LIST: mmsi_list,
                            CONF_RATE_MINUTES: user_input[CONF_RATE_MINUTES],
                            CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return AISFriendsOptionsFlow(config_entry)


class AISFriendsOptionsFlow(config_entries.OptionsFlow):
    """Handle editable vessel and polling options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage AISFriends options."""
        errors: dict[str, str] = {}
        current_mmsi = self._config_entry.options.get(
            CONF_MMSI_LIST, self._config_entry.data.get(CONF_MMSI_LIST, [])
        )
        current_rate = self._config_entry.options.get(
            CONF_RATE_MINUTES,
            self._config_entry.data.get(CONF_RATE_MINUTES, DEFAULT_RATE_MINUTES),
        )
        current_debug = self._config_entry.options.get(
            CONF_DEBUG, self._config_entry.data.get(CONF_DEBUG, False)
        )

        if user_input is not None:
            mmsi_list = _parse_mmsi_input(user_input[CONF_MMSI_LIST])
            if not mmsi_list:
                errors[CONF_MMSI_LIST] = "no_mmsi"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_MMSI_LIST: mmsi_list,
                        CONF_RATE_MINUTES: user_input[CONF_RATE_MINUTES],
                        CONF_DEBUG: user_input.get(CONF_DEBUG, False),
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                mmsi=", ".join(current_mmsi),
                rate=current_rate,
                debug=current_debug,
                include_token=False,
            ),
            errors=errors,
        )

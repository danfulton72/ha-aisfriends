"""Diagnostics support for AISFriends."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import AISFriendsCoordinator
from .const import CONF_DEBUG, CONF_MMSI_LIST, CONF_RATE_MINUTES, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AISFriendsCoordinator = hass.data[DOMAIN][entry.entry_id]

    vessels_info: dict[str, Any] = {}
    for mmsi, vessel in (coordinator.data or {}).items():
        diag = coordinator.diagnostics.get(mmsi, {})
        vessels_info[mmsi] = {
            "parsed_data": vessel,
            "last_http_status": diag.get("last_http_status"),
            "last_url": diag.get("last_url"),
            "last_error": diag.get("last_error"),
            "last_success_time": diag.get("last_success_time"),
            "last_raw_response_excerpt": (diag.get("last_raw_response") or "")[:500],
        }

    return {
        "config": {
            "mmsi_list": entry.options.get(
                CONF_MMSI_LIST, entry.data.get(CONF_MMSI_LIST, [])
            ),
            "rate_minutes": entry.options.get(
                CONF_RATE_MINUTES, entry.data.get(CONF_RATE_MINUTES)
            ),
            "debug_logging": entry.options.get(
                CONF_DEBUG, entry.data.get(CONF_DEBUG, False)
            ),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "vessels": vessels_info,
    }

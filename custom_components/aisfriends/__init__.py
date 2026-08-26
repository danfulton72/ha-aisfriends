"""AISFriends vessel tracking integration."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEBUG,
    CONF_MMSI_LIST,
    CONF_RATE_MINUTES,
    CONF_USERNAME,
    DEFAULT_RATE_MINUTES,
    DIAG_LAST_ERROR,
    DIAG_LAST_HTTP_STATUS,
    DIAG_LAST_RAW_RESPONSE,
    DIAG_LAST_SUCCESS_TIME,
    DIAG_LAST_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]
API_URL = "https://www.aisfriends.com/api/public/v1/vessels/latest-position"
BATCH_SIZE = 10


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AISFriends from a config entry."""
    coordinator = AISFriendsCoordinator(
        hass=hass,
        session=async_get_clientsession(hass),
        token=entry.data[CONF_USERNAME],
        mmsi_list=entry.options.get(CONF_MMSI_LIST, entry.data[CONF_MMSI_LIST]),
        rate_minutes=entry.options.get(
            CONF_RATE_MINUTES,
            entry.data.get(CONF_RATE_MINUTES, DEFAULT_RATE_MINUTES),
        ),
        debug=entry.options.get(CONF_DEBUG, entry.data.get(CONF_DEBUG, False)),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload AISFriends when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an AISFriends config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok


class AISFriendsCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any] | None]]):
    """Coordinate AISFriends vessel position updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        token: str,
        mmsi_list: list[str],
        rate_minutes: int,
        debug: bool,
    ) -> None:
        """Initialize the coordinator."""
        self._session = session
        self._token = token
        self._mmsi_list = [str(mmsi).strip() for mmsi in mmsi_list]
        self._debug = debug
        self.diagnostics: dict[str, dict[str, Any]] = {
            mmsi: {
                DIAG_LAST_RAW_RESPONSE: None,
                DIAG_LAST_HTTP_STATUS: None,
                DIAG_LAST_URL: API_URL,
                DIAG_LAST_ERROR: None,
                DIAG_LAST_SUCCESS_TIME: None,
            }
            for mmsi in self._mmsi_list
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=rate_minutes),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any] | None]:
        """Fetch all configured vessels in API-sized batches."""
        batches = [
            self._mmsi_list[index : index + BATCH_SIZE]
            for index in range(0, len(self._mmsi_list), BATCH_SIZE)
        ]
        responses = await asyncio.gather(*(self._fetch_batch(batch) for batch in batches))
        data: dict[str, dict[str, Any] | None] = {
            mmsi: None for mmsi in self._mmsi_list
        }
        for response in responses:
            data.update(response)
        return data

    async def _fetch_batch(
        self, mmsi_list: list[str]
    ) -> dict[str, dict[str, Any] | None]:
        """Fetch and parse one batch of vessels."""
        mmsi_csv = ",".join(mmsi_list)
        for mmsi in mmsi_list:
            self.diagnostics[mmsi][DIAG_LAST_URL] = f"{API_URL}?mmsi={mmsi_csv}"

        try:
            async with self._session.get(
                API_URL,
                params={"mmsi": mmsi_csv},
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                raw_text = await response.text()
                for mmsi in mmsi_list:
                    self.diagnostics[mmsi][DIAG_LAST_HTTP_STATUS] = response.status
                    self.diagnostics[mmsi][DIAG_LAST_RAW_RESPONSE] = raw_text[:2000]

                if self._debug:
                    _LOGGER.debug(
                        "AISFriends batch %s returned HTTP %s: %s",
                        mmsi_csv,
                        response.status,
                        raw_text[:800],
                    )

                if response.status in (401, 403):
                    raise ConfigEntryAuthFailed("AISFriends API token was rejected")
                if response.status == 429:
                    raise UpdateFailed("AISFriends API rate limit reached")
                if response.status != 200:
                    raise UpdateFailed(
                        f"AISFriends API returned HTTP {response.status}"
                    )

                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError as err:
                    raise UpdateFailed("AISFriends API returned invalid JSON") from err
        except ConfigEntryAuthFailed:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Error communicating with AISFriends: {err}") from err

        result = self._index_batch_response(payload, mmsi_list)
        now = datetime.now(tz=timezone.utc).isoformat()
        for mmsi, vessel in result.items():
            self.diagnostics[mmsi][DIAG_LAST_ERROR] = None if vessel else "No vessel data returned"
            if vessel:
                self.diagnostics[mmsi][DIAG_LAST_SUCCESS_TIME] = now
        return result

    def _index_batch_response(
        self, payload: Any, mmsi_list: list[str]
    ) -> dict[str, dict[str, Any] | None]:
        """Index a list or object API response by MMSI."""
        result: dict[str, dict[str, Any] | None] = {
            mmsi: None for mmsi in mmsi_list
        }
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict) or item.get("mmsi") is None:
                continue
            mmsi = str(item["mmsi"])
            if mmsi in result:
                result[mmsi] = self._parse_vessel(item, mmsi)
        return result

    def _parse_vessel(self, vessel: dict[str, Any], mmsi: str) -> dict[str, Any]:
        """Normalize an AISFriends vessel position object."""
        return {
            "mmsi": vessel.get("mmsi") or mmsi,
            "name": vessel.get("name")
            or vessel.get("reported_name")
            or f"Vessel {mmsi}",
            "latitude": vessel.get("latitude"),
            "longitude": vessel.get("longitude"),
            "navigational_status": vessel.get("navigational_status"),
            "speed_over_ground_knots": vessel.get("speed_over_ground"),
            "destination": vessel.get("ais_destination")
            or vessel.get("destination_port"),
            "eta": self._parse_eta(vessel.get("eta")),
            "course_over_ground": vessel.get("course_over_ground"),
            "true_heading": vessel.get("true_heading"),
            "timestamp": vessel.get("report_timestamp") or vessel.get("timestamp"),
            "imo": vessel.get("imo"),
            "call_sign": vessel.get("call_sign"),
            "type": vessel.get("type"),
            "flag": vessel.get("flag"),
            "country": vessel.get("country"),
            "last_port": vessel.get("last_port"),
            "draught": vessel.get("draught"),
        }

    @staticmethod
    def _parse_eta(eta_raw: Any) -> datetime | None:
        """Parse an API or raw-AIS ETA as a timezone-aware datetime."""
        if not eta_raw:
            return None
        if isinstance(eta_raw, (int, float)):
            if eta_raw == 0:
                return None
            try:
                return datetime.fromtimestamp(eta_raw, tz=timezone.utc)
            except (ValueError, OSError):
                return None

        eta_text = str(eta_raw).strip()
        if eta_text in {"", "0", "00-00 00:00", "00-00 24:60"}:
            return None
        try:
            parsed = datetime.fromisoformat(eta_text.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
        except ValueError:
            pass

        try:
            month_day, hour_minute = eta_text.split()
            month, day = (int(value) for value in month_day.split("-"))
            hour, minute = (int(value) for value in hour_minute.split(":"))
            if not (1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60):
                return None
            now = datetime.now(tz=timezone.utc)
            candidate = datetime(now.year, month, day, hour, minute, tzinfo=timezone.utc)
            if candidate < now - timedelta(days=1):
                candidate = candidate.replace(year=now.year + 1)
            return candidate
        except (ValueError, TypeError):
            return None

"""Device tracker platform for AISFriends."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AISFriendsCoordinator
from .const import (
    ATTR_CALL_SIGN,
    ATTR_COURSE,
    ATTR_DESTINATION,
    ATTR_ETA,
    ATTR_HEADING,
    ATTR_IMO,
    ATTR_NAVIGATIONAL_STATUS,
    ATTR_SPEED_OVER_GROUND,
    ATTR_TIMESTAMP,
    CONF_MMSI_LIST,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AISFriends device trackers from a config entry."""
    coordinator: AISFriendsCoordinator = hass.data[DOMAIN][entry.entry_id]
    mmsi_list = entry.options.get(CONF_MMSI_LIST, entry.data[CONF_MMSI_LIST])

    async_add_entities(
        AISFriendsDeviceTracker(coordinator, mmsi, entry.entry_id)
        for mmsi in mmsi_list
    )


class AISFriendsDeviceTracker(CoordinatorEntity[AISFriendsCoordinator], TrackerEntity):
    """Represent a vessel as a device tracker entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_source_type = SourceType.GPS

    def __init__(
        self,
        coordinator: AISFriendsCoordinator,
        mmsi: str,
        entry_id: str,
    ) -> None:
        """Initialise the tracker."""
        super().__init__(coordinator)
        self._mmsi = mmsi
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{mmsi}_tracker"

    @property
    def _vessel_data(self) -> dict[str, Any] | None:
        """Return current vessel data from the coordinator."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._mmsi)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking all entities for this vessel."""
        data = self._vessel_data
        name = (data or {}).get("name") or f"Vessel {self._mmsi}"
        imo = (data or {}).get("imo")
        return DeviceInfo(
            identifiers={(DOMAIN, self._mmsi)},
            name=name,
            manufacturer="AISFriends",
            model=f"MMSI {self._mmsi}" + (f" / IMO {imo}" if imo else ""),
            configuration_url="https://www.aisfriends.com",
        )

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        data = self._vessel_data
        if data:
            return data.get("latitude")
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        data = self._vessel_data
        if data:
            return data.get("longitude")
        return None

    @property
    def location_accuracy(self) -> int:
        """GPS accuracy in metres (AIS is typically <10 m)."""
        return 10

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self._vessel_data or {}
        eta = data.get("eta")
        return {
            ATTR_NAVIGATIONAL_STATUS: data.get("navigational_status"),
            ATTR_SPEED_OVER_GROUND: data.get("speed_over_ground_knots"),
            ATTR_DESTINATION: data.get("destination"),
            ATTR_ETA: eta.isoformat() if eta else None,
            ATTR_COURSE: data.get("course_over_ground"),
            ATTR_HEADING: data.get("true_heading"),
            ATTR_IMO: data.get("imo"),
            ATTR_CALL_SIGN: data.get("call_sign"),
            ATTR_TIMESTAMP: data.get("timestamp"),
            "mmsi": self._mmsi,
            "type": data.get("type"),
            "flag": data.get("flag"),
            "country": data.get("country"),
            "last_port": data.get("last_port"),
            "draught": data.get("draught"),
        }

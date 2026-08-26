"""Sensor platform for AISFriends – per-vessel entities."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AISFriendsCoordinator
from .const import CONF_MMSI_LIST, DOMAIN


SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="navigational_status",
        name="Navigational Status",
        icon="mdi:ferry",
    ),
    SensorEntityDescription(
        key="destination",
        name="Destination",
        icon="mdi:map-marker-check",
    ),
    SensorEntityDescription(
        key="eta",
        name="ETA",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="speed_over_ground_knots",
        name="Speed Over Ground",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfSpeed.KNOTS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AISFriends sensors from a config entry."""
    coordinator: AISFriendsCoordinator = hass.data[DOMAIN][entry.entry_id]
    mmsi_list = entry.options.get(CONF_MMSI_LIST, entry.data[CONF_MMSI_LIST])

    entities = [
        AISFriendsSensor(coordinator, mmsi, description)
        for mmsi in mmsi_list
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class AISFriendsSensor(CoordinatorEntity[AISFriendsCoordinator], SensorEntity):
    """A single sensor entity for one attribute of one vessel."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AISFriendsCoordinator,
        mmsi: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self._mmsi = mmsi
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{mmsi}_{description.key}"

    @property
    def _vessel_data(self) -> dict[str, Any] | None:
        """Return the current vessel data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._mmsi)

    @property
    def device_info(self) -> DeviceInfo:
        """Link sensor to the vessel device."""
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
    def native_value(self) -> str | float | datetime | None:
        """Return the value for this sensor."""
        data = self._vessel_data
        if not data:
            return None

        key = self.entity_description.key
        value = data.get(key)
        if key == "eta":
            return value
        if key == "speed_over_ground_knots":
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        return None if value is None else str(value)

    @property
    def available(self) -> bool:
        """Return whether data is available for this MMSI."""
        return bool(
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get(self._mmsi) is not None
        )

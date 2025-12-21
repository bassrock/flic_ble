"""Sensor platform for Flic BLE integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL_NAME
from .models import FlicData

if TYPE_CHECKING:
    from homeassistant.components.bluetooth.active_update_processor import (
        ActiveBluetoothProcessorCoordinator,
    )

_LOGGER = logging.getLogger(__name__)

# Sensor entity descriptions
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="battery_level",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,  # Primary sensor
    ),
    SensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,  # Disabled by default
    ),
    SensorEntityDescription(
        key="rssi",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Flic sensors from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    entry_data: dict = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_address, data in entry_data.items():
        if isinstance(data, FlicData):
            # Create all sensor entities for this device
            for description in SENSOR_TYPES:
                entities.append(
                    FlicSensor(
                        coordinator=data.coordinator,
                        device_address=device_address,
                        description=description,
                        entry_title=entry.title,
                    )
                )

    async_add_entities(entities)
    _LOGGER.debug("Added %d Flic sensors", len(entities))


class FlicSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for Flic button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ActiveBluetoothProcessorCoordinator,
        device_address: str,
        description: SensorEntityDescription,
        entry_title: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: ActiveBluetoothProcessorCoordinator instance
            device_address: Bluetooth address of the button
            description: SensorEntityDescription
            entry_title: Title from config entry
        """
        super().__init__(coordinator)
        self.entity_description = description

        # Set unique ID
        self._attr_unique_id = f"{device_address}_{description.key}"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_address)},
            name=entry_title,
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            connections={("bluetooth", device_address)},
        )

        self._device_address = device_address

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value.

        Returns:
            Sensor value or None if not available
        """
        if not self.coordinator.data:
            return None

        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Returns:
            True if sensor data is available
        """
        if not self.coordinator.last_update_success:
            return False

        # Battery sensors require battery data
        if self.entity_description.key in ("battery_level", "battery_voltage"):
            return (
                self.coordinator.data is not None
                and self.coordinator.data.get(self.entity_description.key) is not None
            )

        # RSSI requires data
        if self.entity_description.key == "rssi":
            return (
                self.coordinator.data is not None
                and self.coordinator.data.get("rssi") is not None
            )

        return True

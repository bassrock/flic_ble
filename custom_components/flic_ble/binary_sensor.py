"""Binary sensor platform for Flic BLE integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Flic binary sensors from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    entry_data: dict = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_address, data in entry_data.items():
        if isinstance(data, FlicData):
            entities.append(
                FlicConnectionSensor(
                    coordinator=data.coordinator,
                    device_address=device_address,
                    entry_title=entry.title,
                )
            )

    async_add_entities(entities)
    _LOGGER.debug("Added %d Flic binary sensors", len(entities))


class FlicConnectionSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor showing Flic button connection status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ActiveBluetoothProcessorCoordinator,
        device_address: str,
        entry_title: str,
    ) -> None:
        """Initialize the connection sensor.

        Args:
            coordinator: ActiveBluetoothProcessorCoordinator instance
            device_address: Bluetooth address of the button
            entry_title: Title from config entry
        """
        super().__init__(coordinator)

        # Set unique ID
        self._attr_unique_id = f"{device_address}_connection"
        self._attr_name = "Connection"

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
    def is_on(self) -> bool:
        """Return True if button is connected.

        Returns:
            Connection status
        """
        if not self.coordinator.data:
            return False

        return self.coordinator.data.get("connected", False)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        The connection sensor is always available (even when disconnected),
        it just reports the connection status.

        Returns:
            True (always available)
        """
        return True

"""Event platform for Flic BLE integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EVENT_TYPES, MANUFACTURER, MODEL_NAME
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
    """Set up Flic event entities from a config entry.

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
                FlicButtonEvent(
                    coordinator=data.coordinator,
                    device_address=device_address,
                    entry_title=entry.title,
                    entry_id=entry.entry_id,
                )
            )

            # Also set up event callback on the client to fire HA events for device triggers
            data.client.set_event_callback(
                lambda event_type, event_data: _fire_device_trigger_event(
                    hass, entry.entry_id, device_address, event_type, event_data
                )
            )

    async_add_entities(entities)
    _LOGGER.debug("Added %d Flic event entities", len(entities))


def _fire_device_trigger_event(
    hass: HomeAssistant,
    entry_id: str,
    device_address: str,
    event_type: str,
    event_data: dict,
) -> None:
    """Fire a Home Assistant event for device triggers.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        device_address: Bluetooth address
        event_type: Event type string
        event_data: Additional event data
    """
    # Map event types to device trigger types
    trigger_type_map = {
        "click": "button_short_press",
        "click_release": "button_short_release",
        "double_click": "button_double_press",
        "hold": "button_long_press",
        "hold_release": "button_long_release",
        "click_press": "button_short_press",  # Simplified
        "hold_press": "button_long_press",    # Simplified
    }

    trigger_type = trigger_type_map.get(event_type, event_type)

    # Fire event for device trigger system
    hass.bus.async_fire(
        f"{DOMAIN}_button_event",
        {
            "device_id": f"{DOMAIN}_{device_address}",
            "type": trigger_type,
            "event_type": event_type,
            **event_data,
        },
    )
    _LOGGER.debug("Fired device trigger event: %s (%s)", trigger_type, event_type)


class FlicButtonEvent(CoordinatorEntity, EventEntity):
    """Event entity for Flic button presses."""

    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_name = "Button"

    def __init__(
        self,
        coordinator: ActiveBluetoothProcessorCoordinator,
        device_address: str,
        entry_title: str,
        entry_id: str,
    ) -> None:
        """Initialize the event entity.

        Args:
            coordinator: ActiveBluetoothProcessorCoordinator instance
            device_address: Bluetooth address of the button
            entry_title: Title from config entry
            entry_id: Config entry ID
        """
        super().__init__(coordinator)

        # Set unique ID
        self._attr_unique_id = f"{device_address}_button_event"

        # Set event types
        self._attr_event_types = EVENT_TYPES

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_address)},
            name=entry_title,
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            connections={("bluetooth", device_address)},
        )

        self._device_address = device_address
        self._entry_id = entry_id
        self._last_event_type: str | None = None
        self._last_event_time: str | None = None

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener when entity is added."""
        await super().async_added_to_hass()
        # The coordinator will call _handle_coordinator_update when data changes
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        This is called whenever the coordinator has new data (e.g., button press).
        """
        if not self.coordinator.data:
            return

        event_type = self.coordinator.data.get("last_event_type")
        event_time = self.coordinator.data.get("last_event_time")

        # Only trigger if this is a new event
        if (
            event_type
            and event_type in self._attr_event_types
            and (
                event_type != self._last_event_type
                or event_time != self._last_event_time
            )
        ):
            _LOGGER.debug("Triggering event entity: %s", event_type)

            # Trigger the event
            self._trigger_event(
                event_type,
                {
                    "timestamp": str(event_time) if event_time else None,
                    "battery_level": self.coordinator.data.get("battery_level"),
                },
            )

            # Update state tracking
            self._last_event_type = event_type
            self._last_event_time = event_time

            # Write state
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Returns:
            True if coordinator has valid data
        """
        return self.coordinator.last_update_success

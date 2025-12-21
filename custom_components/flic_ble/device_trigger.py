"""Device trigger support for Flic BLE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, TRIGGER_TYPES

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for Flic buttons.

    Args:
        hass: Home Assistant instance
        device_id: Device ID

    Returns:
        List of trigger configurations
    """
    triggers = []

    # Create a trigger for each trigger type
    for trigger_type, trigger_name in TRIGGER_TYPES.items():
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: trigger_type,
            }
        )

    _LOGGER.debug("Available triggers for device %s: %s", device_id, triggers)
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    trigger_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger.

    Args:
        hass: Home Assistant instance
        config: Trigger configuration
        action: Action to execute when triggered
        trigger_info: Trigger metadata

    Returns:
        Callback to unsubscribe
    """
    trigger_type = config[CONF_TYPE]
    device_id = config[CONF_DEVICE_ID]

    # Get device registry to find the device address
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        _LOGGER.error("Device not found: %s", device_id)
        return lambda: None

    # Extract device address from device connections
    device_address = None
    for connection in device.connections:
        if connection[0] == "bluetooth":
            device_address = connection[1]
            break

    if not device_address:
        _LOGGER.error("No Bluetooth address found for device %s", device_id)
        return lambda: None

    _LOGGER.debug(
        "Attaching trigger: device_id=%s, type=%s, address=%s",
        device_id,
        trigger_type,
        device_address,
    )

    # Create event trigger config
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_button_event",
            event_trigger.CONF_EVENT_DATA: {
                "type": trigger_type,
            },
        }
    )

    # Attach event trigger
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities.

    Args:
        hass: Home Assistant instance
        config: Trigger configuration

    Returns:
        Dictionary with extra fields schema
    """
    # No additional capabilities for now
    return {}

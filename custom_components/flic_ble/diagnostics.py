"""Diagnostics support for Flic BLE integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import FlicData

# Keys to redact from diagnostic data
TO_REDACT = {
    "pairing_key",
    "pairing_identifier",
    "address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        Dictionary with diagnostic data
    """
    entry_data: dict = hass.data[DOMAIN].get(entry.entry_id, {})

    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "devices": {},
    }

    # Collect data for each device
    for device_address, data in entry_data.items():
        if isinstance(data, FlicData):
            client = data.client
            coordinator = data.coordinator

            device_diagnostics = {
                "address": async_redact_data(device_address, TO_REDACT),
                "connection": {
                    "is_connected": client.is_connected,
                    "is_paired": client.is_paired,
                },
                "battery": {
                    "level_percent": client.battery_level,
                    "voltage": client.battery_voltage,
                },
                "coordinator": {
                    "last_update_success": coordinator.last_update_success,
                    "data": coordinator.data,
                },
                "pairing": {
                    "has_identifier": client.pairing_identifier is not None,
                    "has_key": client.pairing_key is not None,
                },
            }

            diagnostics_data["devices"][device_address] = device_diagnostics

    return diagnostics_data

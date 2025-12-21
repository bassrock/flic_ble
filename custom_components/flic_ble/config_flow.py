"""Config flow for Flic BLE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, FLIC_SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class FlicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Flic BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - discover Flic buttons."""
        # Check if Bluetooth is available
        if not bluetooth.async_scanner_count(self.hass, connectable=False):
            return self.async_abort(reason="bluetooth_not_available")

        # Discover Flic buttons
        discovered = bluetooth.async_discovered_service_info(
            self.hass,
            connectable=True
        )

        _LOGGER.debug("Discovered %d BLE devices", len(discovered))

        # Filter for Flic buttons
        # Flic buttons typically have "Flic" in the name or advertise the Flic service UUID
        flic_devices = {}
        for device_info in discovered:
            # Check if it's a Flic button
            if device_info.name and "Flic" in device_info.name:
                display_name = f"{device_info.name} ({device_info.address})"
                flic_devices[display_name] = device_info.address
                _LOGGER.debug("Found Flic button: %s", display_name)
            # Also check for service UUID
            elif FLIC_SERVICE_UUID.lower() in [
                uuid.lower() for uuid in device_info.service_uuids
            ]:
                name = device_info.name or "Flic Button"
                display_name = f"{name} ({device_info.address})"
                flic_devices[display_name] = device_info.address
                _LOGGER.debug("Found Flic button by UUID: %s", display_name)

        if not flic_devices:
            _LOGGER.warning("No Flic buttons found during discovery")
            return self.async_abort(reason="no_devices_found")

        self._discovered_devices = flic_devices

        # If only one device found, skip selection and proceed directly
        if len(flic_devices) == 1:
            device_name = list(flic_devices.keys())[0]
            device_address = list(flic_devices.values())[0]
            return await self._async_create_entry_from_address(
                device_address, device_name
            )

        # Multiple devices - show selection form
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device"): vol.In(flic_devices)
            }),
            description_placeholders={
                "count": str(len(flic_devices))
            }
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any]
    ) -> FlowResult:
        """Handle device selection step."""
        device_display_name = user_input["device"]
        device_address = self._discovered_devices[device_display_name]

        return await self._async_create_entry_from_address(
            device_address, device_display_name
        )

    async def _async_create_entry_from_address(
        self, address: str, name: str
    ) -> FlowResult:
        """Create config entry from device address.

        Args:
            address: Bluetooth MAC address
            name: Display name for the device

        Returns:
            FlowResult for entry creation
        """
        # Set unique ID to prevent duplicate entries
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        # Create shortened display name
        short_name = f"Flic {address[-8:].replace(':', '')}"

        # Create config entry
        # Pairing will happen during first connection
        return self.async_create_entry(
            title=short_name,
            data={
                "address": address,
                "name": name,
            }
        )

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        _LOGGER.debug("Bluetooth discovery: %s", discovery_info)

        address = discovery_info.address
        name = discovery_info.name or f"Flic {address[-8:].replace(':', '')}"

        # Set unique ID to prevent duplicate entries
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        # Store discovery info for confirmation step
        self.context["title_placeholders"] = {"name": name}

        # Show confirmation form
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm Bluetooth discovery."""
        if user_input is None:
            return self.async_show_form(
                step_id="bluetooth_confirm",
                description_placeholders=self.context.get("title_placeholders", {})
            )

        # Get address from unique_id
        address = self.unique_id
        assert address is not None

        name = self.context.get("title_placeholders", {}).get(
            "name",
            f"Flic {address[-8:].replace(':', '')}"
        )

        return await self._async_create_entry_from_address(address, name)

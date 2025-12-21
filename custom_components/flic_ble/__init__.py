"""The Flic BLE integration."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothScanningMode, BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import DEVICE_REGISTRY, DEVICE_SIGNAL, DOMAIN
from .flic.client import FlicClient
from .models import FlicData

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)

# Storage for pairing credentials
PAIRING_STORE_VERSION = 1
PAIRING_STORE_FILENAME = f"{DOMAIN}_pairing.json"


class MockBLEDevice:
    """Mock BLE device for initialization."""

    def __init__(self, address: str) -> None:
        """Initialize mock device."""
        self.address = address
        self.name = f"Flic {address[-8:].replace(':', '')}"


class FlicPairingStore:
    """Store for Flic pairing credentials."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize pairing store."""
        self._store = Store(hass, PAIRING_STORE_VERSION, PAIRING_STORE_FILENAME)

    async def async_save_pairing(
        self, device_address: str, pairing_data: dict
    ) -> None:
        """Save pairing credentials for a device.

        Args:
            device_address: Bluetooth address
            pairing_data: Dict with 'identifier' and 'key'
        """
        all_data = await self._store.async_load() or {}
        all_data[device_address] = pairing_data
        await self._store.async_save(all_data)

    async def async_restore_pairing(self, device_address: str) -> dict | None:
        """Restore pairing credentials for a device.

        Args:
            device_address: Bluetooth address

        Returns:
            Pairing data dict or None if not found
        """
        all_data = await self._store.async_load() or {}
        return all_data.get(device_address)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Flic BLE from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if setup successful
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    entry_data = hass.data[DOMAIN][entry.entry_id]

    # Get device address from config
    device_address = entry.data.get("address")
    if not device_address:
        _LOGGER.error("No device address in config entry")
        raise ConfigEntryNotReady("Missing device address")

    # Initialize pairing store
    pairing_store = FlicPairingStore(hass)

    # Create mock device for initialization
    mock_device = MockBLEDevice(device_address)

    # Create Flic client (coordinator will be set later)
    flic_client = FlicClient(hass, mock_device, coordinator=None)

    # Try to restore pairing credentials
    pairing_data = await pairing_store.async_restore_pairing(device_address)
    if pairing_data:
        flic_client.pairing_identifier = pairing_data.get("identifier")
        flic_client.pairing_key = pairing_data.get("key")
        flic_client.is_paired = True
        _LOGGER.debug(
            "Restored pairing for %s (identifier: %s)",
            device_address,
            flic_client.pairing_identifier
        )

    # Create coordinator methods with proper closure
    def _create_coordinator_methods(
        address: str, client: FlicClient
    ) -> tuple:
        """Create coordinator methods for this device.

        Args:
            address: Device Bluetooth address
            client: FlicClient instance

        Returns:
            Tuple of (update_method, needs_poll_method, poll_method)
        """

        async def _async_update_method(
            service_info: BluetoothServiceInfoBleak
        ) -> dict:
            """Process BLE advertisements.

            Args:
                service_info: Bluetooth service info from advertisement

            Returns:
                Device data dict
            """
            # Store the device info for potential connection
            if service_info.device:
                await client.set_ble_device(service_info.device)

            # Return current data
            return client.data or {}

        def _needs_poll(
            service_info: BluetoothServiceInfoBleak, last_poll: float | None
        ) -> bool:
            """Check if we need to poll the device.

            For Flic buttons, we always want to maintain a persistent connection
            when the device is available.

            Args:
                service_info: Bluetooth service info
                last_poll: Timestamp of last poll

            Returns:
                True if polling needed
            """
            # Only poll when Home Assistant is running
            if hass.state != CoreState.running:
                return False

            # Poll if device is connectable
            return bool(
                bluetooth.async_ble_device_from_address(
                    hass, address, connectable=True
                )
            )

        async def _async_poll(service_info: BluetoothServiceInfoBleak) -> dict:
            """Maintain persistent connection and gather data.

            Args:
                service_info: Bluetooth service info

            Returns:
                Device data dict
            """
            # Get a connectable device from HA
            ble_device = bluetooth.async_ble_device_from_address(
                hass, address, connectable=True
            )
            if not ble_device:
                ble_device = service_info.device if service_info.connectable else None

            if not ble_device:
                _LOGGER.warning("No connectable device found for %s", address)
                return client.data or {}

            await client.set_ble_device(ble_device)

            # Ensure session (connect, pair, subscribe)
            if await client.ensure_session():
                # Read battery level
                await client.get_battery_level()

                # Update data
                client.data = {
                    "connected": client.is_connected,
                    "battery_level": client.battery_level,
                    "battery_voltage": client.battery_voltage,
                    "rssi": service_info.rssi,
                }
                return client.data

            # Return empty data if session failed
            return {}

        return _async_update_method, _needs_poll, _async_poll

    # Get coordinator methods
    update_method, needs_poll_method, poll_method = _create_coordinator_methods(
        device_address, flic_client
    )

    # Create ActiveBluetoothProcessorCoordinator
    coordinator = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=device_address,
        mode=BluetoothScanningMode.ACTIVE,  # Important for persistent connections
        update_method=update_method,
        needs_poll_method=needs_poll_method,
        poll_method=poll_method,
        connectable=True,
    )

    # Set coordinator reference in client
    flic_client.coordinator = coordinator

    # Store in entry data
    entry_data[device_address] = FlicData(
        title=entry.title,
        client=flic_client,
        coordinator=coordinator,
        device_address=device_address,
    )

    # Register in global device registry
    DEVICE_REGISTRY.setdefault(entry.entry_id, {})[device_address] = entry_data[
        device_address
    ]

    # Signal device added
    async_dispatcher_send(hass, f"{DEVICE_SIGNAL}_{entry.entry_id}_{device_address}")

    # Forward to platform setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start coordinator
    entry.async_on_unload(coordinator.async_start())

    # Register shutdown handler
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)
    )

    _LOGGER.info("Flic BLE integration setup complete for %s", device_address)
    return True


async def _async_stop(hass: HomeAssistant, event: Event) -> None:
    """Close all connections on shutdown.

    Args:
        hass: Home Assistant instance
        event: Shutdown event
    """
    domain_data = hass.data.get(DOMAIN, {})
    for entry_id, entry_devices in domain_data.items():
        for addr, data in entry_devices.items():
            if isinstance(data, FlicData):
                try:
                    await data.client.stop_notifications()
                    await data.client.disconnect()
                    _LOGGER.debug("Disconnected Flic button %s", addr)
                except Exception as err:
                    _LOGGER.debug("Error stopping Flic button %s: %s", addr, err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        True if unload successful
    """
    # Get entry devices
    entry_devices = hass.data[DOMAIN].get(entry.entry_id, {})

    # Disconnect all devices
    for addr, data in entry_devices.items():
        if isinstance(data, FlicData):
            try:
                await data.client.stop_notifications()
                await data.client.disconnect()
                _LOGGER.debug("Disconnected Flic button %s during unload", addr)
            except Exception as err:
                _LOGGER.debug("Error disconnecting Flic button %s: %s", addr, err)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok

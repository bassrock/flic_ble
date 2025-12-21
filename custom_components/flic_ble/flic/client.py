"""Flic BLE client implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from ..const import (
    CONNECTION_TIMEOUT,
    FLIC_NOTIFY_CHAR_UUID,
    FLIC_WRITE_CHAR_UUID,
    MAX_CONNECTION_ATTEMPTS,
    OPCODE_BUTTON_EVENT_NOTIFICATION,
    RECONNECT_BACKOFF_BASE,
)
from .protocol import (
    ButtonEvent,
    determine_event_type,
    encode_ack_button_events,
    encode_get_battery_level,
    encode_init_button_events_light,
    encode_quick_verify_request,
    parse_battery_level,
    parse_button_events,
    parse_packet,
    parse_quick_verify_response,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.components.bluetooth.active_update_processor import (
        ActiveBluetoothProcessorCoordinator,
    )

_LOGGER = logging.getLogger(__name__)


class FlicClient:
    """Client for communicating with a Flic button via BLE."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: BLEDevice,
        coordinator: ActiveBluetoothProcessorCoordinator | None = None,
    ) -> None:
        """Initialize the Flic client.

        Args:
            hass: Home Assistant instance
            device: BLE device object
            coordinator: ActiveBluetoothProcessorCoordinator (set after init)
        """
        self.hass = hass
        self.ble_device = device
        self.coordinator = coordinator
        self.client: BleakClient | None = None

        # State tracking
        self.is_connected = False
        self.battery_level: float | None = None
        self.battery_voltage: float | None = None
        self.data: dict[str, Any] = {}

        # Pairing state (will be implemented in Phase 7)
        self.pairing_identifier: int | None = None
        self.pairing_key: bytes | None = None
        self.is_paired = False

        # Event tracking
        self.last_event: ButtonEvent | None = None
        self._event_state: dict[str, Any] = {}

        # Notification callback
        self._event_callback: Callable[[str, dict[str, Any]], None] | None = None

    async def set_ble_device(self, device: BLEDevice) -> None:
        """Update the BLE device object.

        Args:
            device: New BLE device object (may come from proxy)
        """
        self.ble_device = device

    def set_event_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Set callback for button events.

        Args:
            callback: Function to call when button event occurs
                      Parameters: (event_type: str, event_data: dict)
        """
        self._event_callback = callback

    async def connect(self) -> bool:
        """Connect to the Flic button.

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected and self.client and self.client.is_connected:
            return True

        for attempt in range(1, MAX_CONNECTION_ATTEMPTS + 1):
            try:
                _LOGGER.debug(
                    "Attempting to connect to Flic button %s (attempt %d/%d)",
                    self.ble_device.address,
                    attempt,
                    MAX_CONNECTION_ATTEMPTS,
                )

                self.client = BleakClient(self.ble_device)
                await asyncio.wait_for(
                    self.client.connect(),
                    timeout=CONNECTION_TIMEOUT
                )

                if self.client.is_connected:
                    _LOGGER.info("Connected to Flic button %s", self.ble_device.address)
                    self.is_connected = True
                    return True

            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.warning(
                    "Failed to connect to Flic button %s (attempt %d/%d): %s",
                    self.ble_device.address,
                    attempt,
                    MAX_CONNECTION_ATTEMPTS,
                    err,
                )
                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception:
                        pass
                    self.client = None

                if attempt < MAX_CONNECTION_ATTEMPTS:
                    # Exponential backoff
                    await asyncio.sleep(RECONNECT_BACKOFF_BASE ** attempt)

        self.is_connected = False
        return False

    async def disconnect(self) -> None:
        """Disconnect from the Flic button."""
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                _LOGGER.debug("Disconnected from Flic button %s", self.ble_device.address)
            except Exception as err:
                _LOGGER.warning("Error disconnecting from Flic button: %s", err)

        self.is_connected = False
        self.client = None

    async def ensure_session(self) -> bool:
        """Ensure an active session with the Flic button.

        This handles connection, verification (pairing), and notification setup.

        Returns:
            True if session is active, False otherwise
        """
        # Connect if not already connected
        if not await self.connect():
            _LOGGER.error("Failed to connect to Flic button")
            return False

        # Verify/pair if needed
        if not self.is_paired:
            # For now, attempt Quick Verify if we have a pairing identifier
            # Full pairing will be implemented in Phase 7
            if self.pairing_identifier is not None:
                if not await self._quick_verify():
                    _LOGGER.warning("Quick verify failed, full pairing needed")
                    # In Phase 7, we'll implement full pairing here
                    # For now, we'll try to continue without pairing
            else:
                _LOGGER.debug("No pairing identifier, skipping verification for now")
                # In Phase 7, we'll implement full pairing here
                # For now, mark as paired to allow testing
                self.is_paired = True

        # Subscribe to notifications
        if not await self._subscribe_notifications():
            _LOGGER.error("Failed to subscribe to notifications")
            return False

        # Initialize button events
        if not await self._init_button_events():
            _LOGGER.error("Failed to initialize button events")
            return False

        _LOGGER.debug("Session established with Flic button %s", self.ble_device.address)
        return True

    async def _quick_verify(self) -> bool:
        """Perform Quick Verify authentication.

        Returns:
            True if verification successful, False otherwise
        """
        if not self.client or not self.pairing_identifier:
            return False

        try:
            # Send Quick Verify request
            request = encode_quick_verify_request(self.pairing_identifier)
            await self.client.write_gatt_char(FLIC_WRITE_CHAR_UUID, request)

            # Wait for response (simplified - should use notification callback)
            await asyncio.sleep(0.5)

            # In full implementation, we'd parse the response
            # For now, assume success
            self.is_paired = True
            _LOGGER.debug("Quick verify completed")
            return True

        except Exception as err:
            _LOGGER.error("Quick verify failed: %s", err)
            return False

    async def _subscribe_notifications(self) -> bool:
        """Subscribe to button event notifications.

        Returns:
            True if subscription successful, False otherwise
        """
        if not self.client:
            return False

        try:
            await self.client.start_notify(
                FLIC_NOTIFY_CHAR_UUID,
                self._notification_handler
            )
            _LOGGER.debug("Subscribed to Flic notifications")
            return True
        except Exception as err:
            _LOGGER.error("Failed to subscribe to notifications: %s", err)
            return False

    async def stop_notifications(self) -> None:
        """Stop receiving notifications."""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(FLIC_NOTIFY_CHAR_UUID)
                _LOGGER.debug("Stopped Flic notifications")
            except Exception as err:
                _LOGGER.warning("Error stopping notifications: %s", err)

    async def _init_button_events(self) -> bool:
        """Send InitButtonEventsLight request.

        Returns:
            True if request sent successfully, False otherwise
        """
        if not self.client:
            return False

        try:
            request = encode_init_button_events_light()
            await self.client.write_gatt_char(FLIC_WRITE_CHAR_UUID, request)
            _LOGGER.debug("Sent InitButtonEventsLight request")
            return True
        except Exception as err:
            _LOGGER.error("Failed to init button events: %s", err)
            return False

    def _notification_handler(self, sender: int, data: bytes) -> None:
        """Handle incoming BLE notifications.

        This is called by Bleak in a synchronous context.

        Args:
            sender: Characteristic handle
            data: Notification data
        """
        # Schedule async processing
        self.hass.async_create_task(self._async_handle_notification(data))

    async def _async_handle_notification(self, data: bytes) -> None:
        """Process notification data asynchronously.

        Args:
            data: Raw notification bytes
        """
        try:
            packet = parse_packet(data)

            if packet.opcode == OPCODE_BUTTON_EVENT_NOTIFICATION:
                await self._handle_button_events(packet)
            else:
                _LOGGER.debug(
                    "Received packet with opcode %d, length %d",
                    packet.opcode,
                    len(data)
                )

        except Exception as err:
            _LOGGER.error("Error handling notification: %s", err)

    async def _handle_button_events(self, packet: Any) -> None:
        """Handle button event notifications.

        Args:
            packet: Parsed FlicPacket with button events
        """
        try:
            events = parse_button_events(packet)

            if not events:
                return

            # Process each event
            for event in events:
                # Determine high-level event type
                event_type = determine_event_type(
                    event,
                    self.last_event,
                    self._event_state
                )

                _LOGGER.debug(
                    "Button event: %s (raw type: %d, queued: %s)",
                    event_type,
                    event.event_type,
                    event.was_queued
                )

                # Update coordinator data
                if self.coordinator:
                    self.coordinator.async_set_updated_data({
                        "last_event_type": event_type,
                        "last_event_time": event.timestamp,
                        "battery_level": self.battery_level,
                        "battery_voltage": self.battery_voltage,
                        "connected": self.is_connected,
                    })

                # Call event callback if set
                if self._event_callback:
                    self._event_callback(event_type, {
                        "timestamp": event.timestamp,
                        "was_queued": event.was_queued,
                        "age_seconds": event.age_seconds,
                    })

                self.last_event = event

            # Send acknowledgment
            await self._send_ack(len(events))

        except Exception as err:
            _LOGGER.error("Error processing button events: %s", err)

    async def _send_ack(self, event_count: int) -> None:
        """Send acknowledgment for processed events.

        Args:
            event_count: Number of events to acknowledge
        """
        if not self.client:
            return

        try:
            ack = encode_ack_button_events(event_count)
            await self.client.write_gatt_char(FLIC_WRITE_CHAR_UUID, ack)
            _LOGGER.debug("Acknowledged %d button events", event_count)
        except Exception as err:
            _LOGGER.error("Failed to send event acknowledgment: %s", err)

    async def get_battery_level(self) -> float | None:
        """Read battery level from the Flic button.

        Returns:
            Battery percentage (0-100) or None if read failed
        """
        if not self.client or not self.client.is_connected:
            _LOGGER.warning("Cannot read battery: not connected")
            return None

        try:
            # Send battery level request
            request = encode_get_battery_level()
            await self.client.write_gatt_char(FLIC_WRITE_CHAR_UUID, request)

            # Note: In a real implementation, we'd use a notification callback
            # and wait for the response. For now, this is simplified.
            # The battery response will come via notification handler.

            # Return cached value
            return self.battery_level

        except Exception as err:
            _LOGGER.error("Failed to read battery level: %s", err)
            return None

    def _update_battery(self, raw_value: int, voltage: float) -> None:
        """Update cached battery information.

        Args:
            raw_value: Raw battery value from sensor
            voltage: Battery voltage in volts
        """
        # Convert voltage to percentage
        # 2.6V = 0%, 3.0V = 100%
        voltage_range = 3.0 - 2.6
        percentage = max(0, min(100, ((voltage - 2.6) / voltage_range) * 100))

        self.battery_level = round(percentage, 1)
        self.battery_voltage = round(voltage, 2)

        _LOGGER.debug(
            "Battery: %.1f%% (%.2fV, raw: %d)",
            self.battery_level,
            self.battery_voltage,
            raw_value
        )

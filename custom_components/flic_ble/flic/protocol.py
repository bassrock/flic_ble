"""Flic BLE protocol packet parsing and encoding."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..const import (
    BUTTON_EVENT_CLICK,
    BUTTON_EVENT_DOWN,
    BUTTON_EVENT_HOLD,
    BUTTON_EVENT_UP,
    OPCODE_ACK_BUTTON_EVENTS,
    OPCODE_BATTERY_LEVEL_RESPONSE,
    OPCODE_BUTTON_EVENT_NOTIFICATION,
    OPCODE_FULL_VERIFY_REQUEST_1,
    OPCODE_FULL_VERIFY_REQUEST_2,
    OPCODE_FULL_VERIFY_RESPONSE_1,
    OPCODE_FULL_VERIFY_RESPONSE_2,
    OPCODE_GET_BATTERY_LEVEL,
    OPCODE_INIT_BUTTON_EVENTS_LIGHT_REQUEST,
    OPCODE_QUICK_VERIFY_REQUEST,
    OPCODE_QUICK_VERIFY_RESPONSE,
)


@dataclass
class FlicPacket:
    """Base class for Flic protocol packets."""

    opcode: int
    data: bytes


@dataclass
class ButtonEvent:
    """Represents a single button event from the Flic button."""

    event_type: int  # UP, DOWN, CLICK, HOLD
    timestamp: datetime
    was_queued: bool
    age_seconds: float


def parse_packet(data: bytes) -> FlicPacket:
    """Parse a packet received from the Flic button.

    Args:
        data: Raw bytes from the BLE notification

    Returns:
        FlicPacket containing the opcode and payload data
    """
    if len(data) < 1:
        raise ValueError("Packet too short")

    opcode = data[0]
    payload = data[1:] if len(data) > 1 else b""

    return FlicPacket(opcode=opcode, data=payload)


def parse_battery_level(packet: FlicPacket) -> tuple[int, float]:
    """Parse battery level response.

    Args:
        packet: FlicPacket with opcode OPCODE_BATTERY_LEVEL_RESPONSE

    Returns:
        Tuple of (raw_value, voltage) where voltage is in volts
    """
    if packet.opcode != OPCODE_BATTERY_LEVEL_RESPONSE:
        raise ValueError(f"Expected opcode {OPCODE_BATTERY_LEVEL_RESPONSE}, got {packet.opcode}")

    if len(packet.data) < 2:
        raise ValueError("Battery level response too short")

    # Battery level is a 16-bit little-endian value
    battery_raw = struct.unpack("<H", packet.data[0:2])[0]

    # Convert to voltage: voltage = battery_level * 3.6 / 1024
    voltage = battery_raw * 3.6 / 1024.0

    return battery_raw, voltage


def parse_button_events(packet: FlicPacket) -> list[ButtonEvent]:
    """Parse button event notification.

    Args:
        packet: FlicPacket with opcode OPCODE_BUTTON_EVENT_NOTIFICATION

    Returns:
        List of ButtonEvent objects
    """
    if packet.opcode != OPCODE_BUTTON_EVENT_NOTIFICATION:
        raise ValueError(f"Expected opcode {OPCODE_BUTTON_EVENT_NOTIFICATION}, got {packet.opcode}")

    events = []
    offset = 0

    # Each event is 8 bytes:
    # - 6 bytes timestamp (48-bit little-endian, units of 1/32768 second)
    # - 1 byte event_encoded (lower 2 bits = event type, bit 2 = was_queued)
    # - 1 byte age (age in seconds * 4)
    while offset + 8 <= len(packet.data):
        event_data = packet.data[offset:offset + 8]

        # Parse timestamp (48-bit LE)
        timestamp_raw = struct.unpack("<Q", event_data[0:6] + b"\x00\x00")[0]
        # Convert to seconds (divide by 32768 Hz)
        timestamp_seconds = timestamp_raw / 32768.0

        # Parse event_encoded byte
        event_encoded = event_data[6]
        event_type = event_encoded & 0x03  # Lower 2 bits
        was_queued = bool(event_encoded & 0x04)  # Bit 2

        # Parse age
        age_raw = event_data[7]
        age_seconds = age_raw / 4.0

        # Create timestamp from age (approximate)
        # Note: For real-time events, age will be near 0
        # For queued events, we can calculate when it actually occurred
        event_time = datetime.now(timezone.utc)

        events.append(
            ButtonEvent(
                event_type=event_type,
                timestamp=event_time,
                was_queued=was_queued,
                age_seconds=age_seconds,
            )
        )

        offset += 8

    return events


def determine_event_type(
    event: ButtonEvent, previous_event: ButtonEvent | None, pending_state: dict[str, Any]
) -> str:
    """Determine the high-level event type (click, double_click, hold, etc.).

    Args:
        event: Current button event
        previous_event: Previous button event (if any)
        pending_state: Dictionary to track state between events

    Returns:
        Event type string (click, double_click, hold, etc.)
    """
    event_type = event.event_type

    if event_type == BUTTON_EVENT_DOWN:
        # Track down event time for hold detection
        pending_state["last_down_time"] = event.timestamp
        pending_state["is_hold"] = False
        return "click_press"

    elif event_type == BUTTON_EVENT_UP:
        # Determine if this was a hold or click release
        if pending_state.get("is_hold"):
            pending_state["is_hold"] = False
            return "hold_release"
        else:
            # Check for potential double click
            # (This is simplified - real implementation would use timers)
            return "click_release"

    elif event_type == BUTTON_EVENT_CLICK:
        # Single click timeout reached
        return "click"

    elif event_type == BUTTON_EVENT_HOLD:
        # Hold event (down for > 1 second)
        pending_state["is_hold"] = True
        return "hold"

    return "unknown"


def encode_get_battery_level() -> bytes:
    """Encode a GetBatteryLevel request packet.

    Returns:
        Bytes to send to the Flic button
    """
    return bytes([OPCODE_GET_BATTERY_LEVEL])


def encode_ack_button_events(event_count: int) -> bytes:
    """Encode an AckButtonEvents packet.

    Args:
        event_count: Number of events to acknowledge

    Returns:
        Bytes to send to the Flic button
    """
    return struct.pack("<BI", OPCODE_ACK_BUTTON_EVENTS, event_count)


def encode_init_button_events_light() -> bytes:
    """Encode an InitButtonEventsLight request packet.

    This requests the button to start sending button event notifications.

    Returns:
        Bytes to send to the Flic button
    """
    return bytes([OPCODE_INIT_BUTTON_EVENTS_LIGHT_REQUEST])


def encode_quick_verify_request(pairing_identifier: int) -> bytes:
    """Encode a QuickVerify request packet.

    Args:
        pairing_identifier: 32-bit pairing identifier from previous Full Verify

    Returns:
        Bytes to send to the Flic button
    """
    return struct.pack("<BI", OPCODE_QUICK_VERIFY_REQUEST, pairing_identifier)


def parse_quick_verify_response(packet: FlicPacket) -> dict[str, Any]:
    """Parse a QuickVerify response packet.

    Args:
        packet: FlicPacket with opcode OPCODE_QUICK_VERIFY_RESPONSE

    Returns:
        Dictionary with response data
    """
    if packet.opcode != OPCODE_QUICK_VERIFY_RESPONSE:
        raise ValueError(f"Expected opcode {OPCODE_QUICK_VERIFY_RESPONSE}, got {packet.opcode}")

    if len(packet.data) < 1:
        raise ValueError("QuickVerify response too short")

    # First byte is success/failure
    success = packet.data[0] == 1

    return {"success": success}


# Pairing-related functions (Full Verify) will be added in Phase 7
# For now, these are placeholders to allow basic connection testing

def encode_full_verify_request_1(device_address: str) -> bytes:
    """Encode a FullVerify request packet (step 1).

    Note: Full implementation requires cryptographic operations.
    This is a placeholder for Phase 7.

    Args:
        device_address: Bluetooth address of the button

    Returns:
        Bytes to send to the Flic button
    """
    # Placeholder - full implementation in Phase 7
    return bytes([OPCODE_FULL_VERIFY_REQUEST_1])


def parse_full_verify_response_1(packet: FlicPacket) -> dict[str, Any]:
    """Parse FullVerify response packet (step 1).

    Note: Full implementation requires cryptographic operations.
    This is a placeholder for Phase 7.

    Args:
        packet: FlicPacket with opcode OPCODE_FULL_VERIFY_RESPONSE_1

    Returns:
        Dictionary with response data
    """
    # Placeholder - full implementation in Phase 7
    return {"data": packet.data}

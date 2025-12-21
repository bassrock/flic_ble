"""Constants for the Flic BLE integration."""
from __future__ import annotations

# Integration domain
DOMAIN = "flic_ble"

# Bluetooth UUIDs (from Flic 2 Protocol Specification)
FLIC_SERVICE_UUID = "00420000-8f59-4420-870d-84f3b617e493"
FLIC_WRITE_CHAR_UUID = "00420001-8f59-4420-870d-84f3b617e493"
FLIC_NOTIFY_CHAR_UUID = "00420002-8f59-4420-870d-84f3b617e493"

# Protocol opcodes
OPCODE_GET_BATTERY_LEVEL = 20
OPCODE_BATTERY_LEVEL_RESPONSE = 21
OPCODE_FULL_VERIFY_REQUEST_1 = 28
OPCODE_FULL_VERIFY_RESPONSE_1 = 29
OPCODE_FULL_VERIFY_REQUEST_2 = 30
OPCODE_FULL_VERIFY_RESPONSE_2 = 31
OPCODE_QUICK_VERIFY_REQUEST = 32
OPCODE_QUICK_VERIFY_RESPONSE = 33
OPCODE_INIT_BUTTON_EVENTS_LIGHT_REQUEST = 40
OPCODE_BUTTON_EVENT_NOTIFICATION = 41
OPCODE_ACK_BUTTON_EVENTS = 42

# Event types for Event entities
EVENT_TYPES = [
    "click",
    "double_click",
    "hold",
    "click_press",
    "click_release",
    "hold_press",
    "hold_release",
]

# Device trigger types (for blueprints/automations)
TRIGGER_TYPES = {
    "button_short_press": "Short press",
    "button_double_press": "Double press",
    "button_long_press": "Long press",
    "button_short_release": "Short release",
    "button_long_release": "Long release",
}

# Button event types (from protocol spec)
BUTTON_EVENT_UP = 0
BUTTON_EVENT_DOWN = 1
BUTTON_EVENT_CLICK = 2
BUTTON_EVENT_HOLD = 3

# Connection constants
CONNECTION_TIMEOUT = 10  # seconds
MAX_CONNECTION_ATTEMPTS = 5
RECONNECT_BACKOFF_BASE = 2  # seconds

# Battery constants
BATTERY_VOLTAGE_MIN = 2.6  # V (0%)
BATTERY_VOLTAGE_MAX = 3.0  # V (100%)
BATTERY_VOLTAGE_SCALE = 3.6 / 1024.0

# Device registry
DEVICE_REGISTRY = {}
DEVICE_SIGNAL = f"{DOMAIN}_device_added"

# Manufacturer info
MANUFACTURER = "Shortcut Labs"
MODEL_NAME = "Flic 2"

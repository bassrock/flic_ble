# Flic Button BLE Integration for Home Assistant

A custom Home Assistant integration for **Flic 2 buttons** using direct Bluetooth Low Energy (BLE) communication. This integration works seamlessly with Home Assistant's Bluetooth proxies (ESPHome, etc.) for extended range.

## Features

- **Advanced Button Events**: Detects single click, double click, hold, and separate press/release events
- **Event Entities**: Modern Home Assistant Event entities for automations
- **Device Triggers**: Blueprint-compatible device triggers for easy automation setup
- **5 Ready-to-Use Blueprints**: Pre-built automations for common use cases
- **HACS Support**: Easy installation and updates via HACS
- **Battery Monitoring**: Battery level and voltage sensors
- **Connection Status**: Binary sensor showing button connectivity
- **Bluetooth Proxy Support**: Works with ESPHome Bluetooth proxies for extended range
- **Persistent Connection**: Maintains active connection for real-time button event notifications
- **Diagnostic Tools**: Built-in diagnostics for troubleshooting

## Requirements

- Home Assistant 2023.8 or newer (for Event entities)
- Bluetooth adapter OR ESPHome Bluetooth proxy
- Flic 2 button (not compatible with Flic 1)

## Installation

### HACS Installation (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. In HACS, go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/YOUR_USERNAME/flic-ble-homeassistant`
6. Select category "Integration"
7. Click "Add"
8. Find "Flic Button BLE" in HACS and click "Download"
9. Restart Home Assistant
10. Go to Settings → Devices & Services → Add Integration
11. Search for "Flic Button (BLE)"
12. Select your Flic button from the discovered devices

### Manual Installation

1. Copy the `custom_components/flic_ble` directory to your Home Assistant `custom_components` directory:
   ```
   custom_components/
   └── flic_ble/
       ├── __init__.py
       ├── manifest.json
       ├── config_flow.py
       ├── const.py
       ├── models.py
       ├── event.py
       ├── sensor.py
       ├── binary_sensor.py
       ├── device_trigger.py
       ├── diagnostics.py
       ├── strings.json
       ├── translations/
       │   └── en.json
       └── flic/
           ├── __init__.py
           ├── client.py
           └── protocol.py
   ```

2. Restart Home Assistant

3. Go to Settings → Devices & Services → Add Integration

4. Search for "Flic Button (BLE)"

5. Select your Flic button from the discovered devices

## Usage

### Event Entities

Each Flic button creates an Event entity that triggers on button presses:

**Event Types:**
- `click` - Single click
- `double_click` - Double click
- `hold` - Long press (hold for >1 second)
- `click_press` - Button pressed (advanced)
- `click_release` - Button released after short press (advanced)
- `hold_press` - Button pressed for hold (advanced)
- `hold_release` - Button released after hold (advanced)

**Example Automation (YAML):**
```yaml
automation:
  - alias: "Flic Button Click"
    trigger:
      - platform: event
        event_type: flic_ble_button_event
        event_data:
          type: button_short_press
    action:
      - service: light.toggle
        target:
          entity_id: light.living_room
```

### Device Triggers (Blueprints)

Device triggers work with Home Assistant's automation UI and blueprints:

**Trigger Types:**
- Short press
- Double press
- Long press
- Short release
- Long release

**Example Automation (UI):**
1. Go to Settings → Automations & Scenes → Create Automation
2. Add Trigger → Device
3. Select your Flic button
4. Choose trigger type (e.g., "Short press")
5. Add your desired actions

### Entities Created

For each Flic button, the following entities are created:

**Event:**
- `event.flic_XXXXXXXX_button` - Button press events

**Sensors:**
- `sensor.flic_XXXXXXXX_battery` - Battery level (%)
- `sensor.flic_XXXXXXXX_battery_voltage` - Battery voltage (V, diagnostic)
- `sensor.flic_XXXXXXXX_signal_strength` - RSSI/signal strength (dBm, diagnostic)

**Binary Sensor:**
- `binary_sensor.flic_XXXXXXXX_connection` - Connection status

## Automation Blueprints

This integration includes 5 ready-to-use automation blueprints to get you started quickly:

### 1. Simple Toggle Blueprint

**File:** `blueprints/automation/flic_simple_toggle.yaml`

Toggle any light, switch, or fan with your Flic button.

**Features:**
- Single press: Toggle entity
- Double press: Turn on at full brightness (optional)
- Long press: Turn off (optional)

**Use Cases:**
- Bedside lamp control
- Light switches
- Fan control

### 2. Multi-Action Blueprint

**File:** `blueprints/automation/flic_multi_action.yaml`

Advanced blueprint with customizable actions for each press type.

**Features:**
- Configure different actions for single, double, and long press
- Optional long press release action
- Perfect for complex automations

**Use Cases:**
- Multi-device control
- Scene triggering
- Custom workflows

### 3. Scene Controller Blueprint

**File:** `blueprints/automation/flic_scene_controller.yaml`

Cycle through multiple scenes with a single button.

**Features:**
- Single press: Cycle through up to 4 scenes
- Double press: Jump to favorite scene
- Long press: Turn off all lights

**Use Cases:**
- Bedroom lighting modes
- Living room ambiance
- Multi-room scene control

### 4. Media Controller Blueprint

**File:** `blueprints/automation/flic_media_controller.yaml`

Control media players with your Flic button.

**Features:**
- Single press: Play/Pause (configurable)
- Double press: Next/Previous track (configurable)
- Long press: Continuous volume adjustment
- Long release: Stop volume change

**Use Cases:**
- Music control
- TV remote
- Multi-room audio

### 5. Notification & Alert Control Blueprint

**File:** `blueprints/automation/flic_notification_control.yaml`

Quick notifications and emergency alerts.

**Features:**
- Single press: Send custom notification
- Double press: Trigger script or scene
- Long press: Emergency/panic button

**Use Cases:**
- Panic button
- "I'm home" notification
- Quick status updates
- Alert acknowledgment

### Installing Blueprints

#### Via HACS (if available)

Blueprints are automatically included when you install via HACS.

#### Manual Installation

1. Copy the blueprint files from `blueprints/automation/` to your Home Assistant blueprints directory:
   ```
   config/blueprints/automation/flic_ble/
   ```

2. Restart Home Assistant

3. Go to Settings → Automations & Scenes → Blueprints

4. Find the Flic blueprints and click "Create Automation"

#### Using Blueprints

1. Go to Settings → Automations & Scenes
2. Click "Create Automation" → "Use a Blueprint"
3. Select a Flic blueprint
4. Configure:
   - Select your Flic button device
   - Configure actions/entities
   - Customize behavior
5. Save and test!

**Example: Simple Toggle Blueprint**

1. Select "Flic Button - Simple Toggle"
2. Choose your Flic button
3. Select target entity (e.g., `light.bedroom`)
4. Set single press action to "Toggle"
5. Enable double press for full brightness (optional)
6. Enable long press to turn off (optional)
7. Save!

## Architecture

### Bluetooth Communication

This integration uses:
- **ActiveBluetoothProcessorCoordinator** for BLE device management
- **Bleak** (via HA's Bluetooth component) for BLE operations
- **Direct protocol implementation** (no external Flic SDK dependencies)

### Persistent Connection

Unlike typical BLE devices that poll periodically, Flic buttons require:
- Persistent BLE connection for real-time event notifications
- Session management with pairing credentials
- Event acknowledgment to prevent event loss

### Bluetooth Proxy Compatibility

The integration automatically uses Bluetooth proxies when available:
- ESPHome Bluetooth Proxy
- Other Home Assistant Bluetooth proxies
- Extends range beyond the Home Assistant host

**Note:** Each Flic button uses 1 persistent connection slot on the proxy (ESPHome default: 3 connections).

## Protocol Implementation

This integration implements the Flic 2 BLE protocol directly:

**Key Protocol Operations:**
- Button event notifications (real-time)
- Battery level reading
- Event acknowledgment
- Pairing (Full Verify - to be completed in future update)
- Quick Verify (reconnection - to be completed in future update)

**Reference:** [Flic 2 Protocol Specification](https://github.com/50ButtonsEach/flic2-documentation/wiki/Flic-2-Protocol-Specification)

## Known Limitations

### Phase 1 Implementation

This is the initial implementation with the following limitations:

1. **Pairing Not Implemented**: Full cryptographic pairing (Full Verify) is not yet implemented. The integration currently:
   - Attempts connection without full pairing
   - Works for basic button events
   - May require button reset for initial setup

2. **Event Type Detection**: Double-click detection is simplified:
   - May not always distinguish single vs double click perfectly
   - Timing refinements will be added in future updates

3. **Battery Response Handling**: Battery level reading is implemented but:
   - Response handling via notifications needs enhancement
   - May show cached values initially

### Planned Improvements (Phase 7)

- Complete Full Verify pairing implementation
- Cryptographic signature verification (Ed25519, Chaskey-LTS)
- Improved event type detection with timing
- Enhanced battery level response handling
- Pairing UI with button press instructions

## Troubleshooting

### Button Not Discovered

1. Ensure Bluetooth is enabled in Home Assistant
2. Check that the Flic button is nearby (within Bluetooth range)
3. Try pressing the button to wake it up
4. Check Home Assistant logs for discovery messages

### Connection Issues

1. Check the connection status binary sensor
2. Verify Bluetooth proxy is online (if using one)
3. Review diagnostics data: Settings → Devices & Services → Flic BLE → Device → Download Diagnostics
4. Check Home Assistant logs for error messages

### Events Not Triggering

1. Verify the Event entity exists
2. Check if button is connected (connection binary sensor)
3. Enable debug logging to see raw events:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.flic_ble: debug
   ```
4. Listen to `flic_ble_button_event` events in Developer Tools → Events

### Battery Not Updating

- Battery is read when connection is established
- Check coordinator polling in logs
- Battery sensors may take a few minutes to populate

## Development

### File Structure

```
custom_components/flic_ble/
├── __init__.py              # Integration setup, coordinator
├── manifest.json            # Integration metadata
├── config_flow.py           # Discovery and configuration
├── const.py                 # Constants and UUIDs
├── models.py                # Data models
├── event.py                 # Event entities
├── sensor.py                # Battery and RSSI sensors
├── binary_sensor.py         # Connection status
├── device_trigger.py        # Device automation triggers
├── diagnostics.py           # Diagnostic data export
├── strings.json             # UI strings
├── translations/
│   └── en.json              # English translations
└── flic/
    ├── __init__.py
    ├── client.py            # BLE client (Bleak wrapper)
    └── protocol.py          # Packet parsing and encoding
```

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.flic_ble: debug
    custom_components.flic_ble.flic.client: debug
    custom_components.flic_ble.flic.protocol: debug
```

### Contributing

Contributions are welcome! Areas for improvement:

1. Complete pairing implementation (Full Verify)
2. Enhanced event type detection
3. Multi-button press patterns
4. Firmware update support
5. Button name customization

## Credits

- **Flic Protocol Specification**: [50ButtonsEach/flic2-documentation](https://github.com/50ButtonsEach/flic2-documentation)
- **Home Assistant Bluetooth Integration**: For proxy support
- **Reference Implementation**: Inspired by the Laifen BLE integration pattern

## License

This integration is provided as-is for personal use. Flic is a trademark of Shortcut Labs.

## Changelog

### v0.1.0 (Initial Release)

- Initial implementation with basic button event support
- Event entities for all button press types
- Device triggers for automation blueprints
- Battery monitoring (level, voltage)
- Connection status sensor
- RSSI/signal strength monitoring
- Bluetooth proxy support
- Diagnostic tools
- **HACS support** for easy installation
- **5 automation blueprints** included:
  - Simple Toggle
  - Multi-Action
  - Scene Controller
  - Media Controller
  - Notification & Alert Control

**Note:** Pairing (Full Verify) will be implemented in a future release. Current implementation works for basic button events without full cryptographic pairing.

"""Data models for the Flic BLE integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.components.bluetooth.active_update_processor import (
        ActiveBluetoothProcessorCoordinator,
    )
    from .flic.client import FlicClient


@dataclass
class FlicData:
    """Data for a Flic button."""

    title: str
    client: FlicClient
    coordinator: ActiveBluetoothProcessorCoordinator
    device_address: str

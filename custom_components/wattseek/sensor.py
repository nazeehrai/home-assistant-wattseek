from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FLOW_SENSOR_MAP, DETAIL_SENSOR_NAMES
from .entity import WattSeekEntity, slugify


DEVICE_CLASS_MAP = {
    "power": SensorDeviceClass.POWER,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "frequency": SensorDeviceClass.FREQUENCY,
    "battery": SensorDeviceClass.BATTERY,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "energy": SensorDeviceClass.ENERGY,
    "apparent_power": SensorDeviceClass.APPARENT_POWER,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key, (name, unit, device_class) in FLOW_SENSOR_MAP.items():
        entities.append(WattSeekFlowSensor(coordinator, key, name, unit, device_class))

    for attr_name, (name, unit, device_class) in DETAIL_SENSOR_NAMES.items():
        entities.append(WattSeekDetailSensor(coordinator, attr_name, name, unit, device_class))

    async_add_entities(entities)


class _BaseSensor(WattSeekEntity, SensorEntity):
    def _configure(self, name: str, unit: str | None, device_class: str | None) -> None:
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = DEVICE_CLASS_MAP.get(device_class)
        if device_class == "energy":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif device_class in {"power", "voltage", "current", "frequency", "temperature"}:
            self._attr_state_class = SensorStateClass.MEASUREMENT


class WattSeekFlowSensor(_BaseSensor):
    def __init__(self, coordinator, source_key, name, unit, device_class):
        self.source_key = source_key
        super().__init__(coordinator, f"flow_{source_key}")
        self._configure(name, unit, device_class)

    @property
    def native_value(self):
        value = (self.coordinator.data or {}).get("flow", {}).get(self.source_key)

        # Normalize battery power for Home Assistant energy-flow consumers:
        # negative means charging, positive means discharging.
        # WattSeek reports power as a magnitude; Battery current provides
        # the direction.
        if self.source_key == "batteryPower" and value is not None:
            try:
                magnitude = abs(float(value))
            except (TypeError, ValueError):
                return value

            current = (self.coordinator.data or {}).get(
                "detail_flat", {}
            ).get("Battery current")
            try:
                current = float(current)
            except (TypeError, ValueError):
                return None

            if current < -0.2:
                return -magnitude
            if current > 0.2:
                return magnitude
            return 0.0

        return value


class WattSeekDetailSensor(_BaseSensor):
    def __init__(self, coordinator, attr_name, name, unit, device_class):
        self.attr_name = attr_name
        super().__init__(coordinator, f"detail_{slugify(attr_name)}")
        self._configure(name, unit, device_class)

    @property
    def native_value(self):
        value = (self.coordinator.data or {}).get("detail_flat", {}).get(self.attr_name)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

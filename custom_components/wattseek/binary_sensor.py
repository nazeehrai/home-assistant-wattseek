from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WattSeekEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WattSeekOnlineSensor(coordinator),
        WattSeekGridConnectedSensor(coordinator),
    ])


class WattSeekOnlineSensor(WattSeekEntity, BinarySensorEntity):
    _attr_name = "Inverter Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator):
        super().__init__(coordinator, "online")

    @property
    def is_on(self):
        detail = (self.coordinator.data or {}).get("detail", {})
        return detail.get("deviceConnectStatus") == "ONLINE"


class WattSeekGridConnectedSensor(WattSeekEntity, BinarySensorEntity):
    _attr_name = "Grid Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator):
        super().__init__(coordinator, "grid_connected")

    @property
    def is_on(self):
        v = (self.coordinator.data or {}).get("detail_flat", {}).get("Grid voltage")
        try:
            return float(v) > 50
        except (TypeError, ValueError):
            return False

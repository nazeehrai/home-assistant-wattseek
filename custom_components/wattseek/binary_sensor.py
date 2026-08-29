from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import WattSeekEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WattSeekOnlineSensor(coordinator),
        WattSeekGridConnectedSensor(coordinator),
        *(
            WattSeekGroupPendingSensor(coordinator, group)
            for group in coordinator.iter_groups()
        ),
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


class WattSeekGroupPendingSensor(WattSeekEntity, BinarySensorEntity):
    _attr_icon = "mdi:content-save-alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, group):
        self.group_id = str(group["groupId"])
        self.group_name = str(group.get("groupName") or self.group_id)
        super().__init__(coordinator, f"group_{self.group_id}_pending")
        self._attr_name = f"{self.group_name} — Pending changes"

    @property
    def is_on(self):
        return self.coordinator.has_pending_changes(self.group_id)

    @property
    def extra_state_attributes(self):
        return {
            "wattseek_group": self.group_name,
            "pending_count": len(
                self.coordinator.pending_values.get(self.group_id, {})
            ),
        }

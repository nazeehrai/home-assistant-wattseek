from __future__ import annotations

import re
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import WattSeekCoordinator


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


class WattSeekEntity(CoordinatorEntity[WattSeekCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WattSeekCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.api.device_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        d = self.coordinator.api.device or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.api.device_id)},
            name=d.get("deviceName") or d.get("deviceSn") or "WattSeek Inverter",
            manufacturer="WattSeek",
            model=d.get("deviceModel"),
            serial_number=d.get("deviceSn"),
        )


class WattSeekCommandEntity(WattSeekEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WattSeekCoordinator, command: dict[str, Any]) -> None:
        self.command = command
        self.cmd_id = str(command["cmdId"])
        self.group_id = str(command["groupId"])
        super().__init__(coordinator, f"cmd_{self.cmd_id}")
        self._attr_name = (
            f"{coordinator.group_name(self.group_id)} — "
            f"{command.get('cmdName') or self.cmd_id}"
        )

    @property
    def raw_value(self) -> Any:
        return self.coordinator.effective_value(self.group_id, self.cmd_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pending = self.coordinator.pending_values.get(self.group_id, {})
        return {
            "wattseek_group": self.coordinator.group_name(self.group_id),
            "confirmed_value": self.coordinator.confirmed_value(self.cmd_id),
            "pending_value": pending.get(self.cmd_id),
            "pending_change": self.cmd_id in pending,
        }

    async def async_write(self, value: Any) -> None:
        self.coordinator.stage_value(self.group_id, self.cmd_id, value)

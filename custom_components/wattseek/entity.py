from __future__ import annotations

import re
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

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
    def __init__(self, coordinator: WattSeekCoordinator, command: dict[str, Any]) -> None:
        self.command = command
        self.cmd_id = str(command["cmdId"])
        self.group_id = str(command["groupId"])
        super().__init__(coordinator, f"cmd_{self.cmd_id}")
        self._attr_name = command.get("cmdName") or self.cmd_id

    @property
    def raw_value(self) -> Any:
        return (self.coordinator.data or {}).get("command_values", {}).get(self.cmd_id)

    async def async_write(self, value: Any) -> None:
        await self.coordinator.async_write_command(self.group_id, self.cmd_id, value)

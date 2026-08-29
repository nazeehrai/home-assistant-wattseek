from __future__ import annotations

import json

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WattSeekCommandEntity
from .select import iter_commands


def _range_from_value(raw):
    if not raw or not isinstance(raw, str):
        return None
    try:
        value = json.loads(raw)
        if isinstance(value, list) and len(value) == 2:
            return value
    except Exception:
        return None
    return None


def _applicable_range(command, current_values):
    ranges = []
    for item in command.get("cmdValueList") or []:
        r = _range_from_value(item.get("value"))
        if not r:
            continue
        linkage = item.get("linkage")
        if linkage and ":" in linkage:
            linked_cmd, expected = linkage.split(":", 1)
            if str(current_values.get(linked_cmd)) != expected:
                continue
        ranges.append(r)
    if not ranges:
        for item in command.get("cmdValueList") or []:
            r = _range_from_value(item.get("value"))
            if r:
                ranges.append(r)
    if not ranges:
        return None
    return min(x[0] for x in ranges), max(x[1] for x in ranges)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        WattSeekNumber(coordinator, cmd)
        for cmd in iter_commands(coordinator.protocol)
        if cmd.get("interactiveMode") == "INPUT"
    ]
    async_add_entities(entities)


class WattSeekNumber(WattSeekCommandEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, command):
        super().__init__(coordinator, command)
        self._attr_native_unit_of_measurement = command.get("unit")

    @property
    def native_value(self):
        try:
            return float(self.raw_value)
        except (TypeError, ValueError):
            return None

    @property
    def native_min_value(self):
        values = self.coordinator.effective_command_values()
        r = _applicable_range(self.command, values)
        return float(r[0]) if r else 0.0

    @property
    def native_max_value(self):
        values = self.coordinator.effective_command_values()
        r = _applicable_range(self.command, values)
        return float(r[1]) if r else 100000.0

    @property
    def native_step(self):
        accuracy = self.command.get("accuracy")
        try:
            decimal_places = int(accuracy)
            if decimal_places >= 0:
                return 10 ** (-decimal_places)
        except (TypeError, ValueError):
            pass
        return 1.0

    async def async_set_native_value(self, value: float) -> None:
        try:
            decimal_places = max(0, int(self.command.get("accuracy") or 0))
        except (TypeError, ValueError):
            decimal_places = 0
        if decimal_places:
            text = f"{value:.{decimal_places}f}"
        else:
            text = str(int(value) if float(value).is_integer() else value)
        await self.async_write(text)

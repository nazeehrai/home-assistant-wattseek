from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DANGEROUS_COMMAND_NAMES
from .entity import WattSeekCommandEntity


def iter_commands(protocol):
    for group in (protocol or {}).get("cmdGroupList", []) or []:
        for cmd in group.get("cmdList", []) or []:
            yield cmd


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for cmd in iter_commands(coordinator.protocol):
        if cmd.get("interactiveMode") != "SELECT":
            continue
        options = cmd.get("cmdValueList") or []
        # Two-state OFF/ON controls are exposed as switches instead.
        texts = [str(x.get("text")) for x in options]
        if len(options) == 2 and set(texts) <= {"OFF", "ON", "Disable", "Enable"}:
            continue
        entities.append(WattSeekSelect(coordinator, cmd))
    async_add_entities(entities)


class WattSeekSelect(WattSeekCommandEntity, SelectEntity):
    def __init__(self, coordinator, command):
        super().__init__(coordinator, command)
        self._choices = command.get("cmdValueList") or []
        self._text_to_value = {str(x.get("text")): str(x.get("value")) for x in self._choices}
        self._value_to_text = {str(x.get("value")): str(x.get("text")) for x in self._choices}
        self._attr_options = list(self._text_to_value)
        if self._attr_name in DANGEROUS_COMMAND_NAMES:
            self._attr_entity_registry_enabled_default = False

    @property
    def current_option(self):
        if self.raw_value is None:
            return None
        return self._value_to_text.get(str(self.raw_value), str(self.raw_value))

    async def async_select_option(self, option: str) -> None:
        await self.async_write(self._text_to_value[option])

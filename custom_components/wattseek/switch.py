from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DANGEROUS_COMMAND_NAMES
from .entity import WattSeekCommandEntity
from .select import iter_commands


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for cmd in iter_commands(coordinator.protocol):
        if cmd.get("interactiveMode") != "SELECT":
            continue
        options = cmd.get("cmdValueList") or []
        texts = [str(x.get("text")) for x in options]
        if len(options) != 2 or not set(texts) <= {"OFF", "ON", "Disable", "Enable"}:
            continue
        entities.append(WattSeekSwitch(coordinator, cmd))
    async_add_entities(entities)


class WattSeekSwitch(WattSeekCommandEntity, SwitchEntity):
    def __init__(self, coordinator, command):
        super().__init__(coordinator, command)
        options = command.get("cmdValueList") or []
        self._on_value = next((str(x["value"]) for x in options if str(x.get("text")) in {"ON", "Enable"}), "1")
        self._off_value = next((str(x["value"]) for x in options if str(x.get("text")) in {"OFF", "Disable"}), "0")
        if command.get("cmdName") in DANGEROUS_COMMAND_NAMES:
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self):
        return str(self.raw_value) == self._on_value

    async def async_turn_on(self, **kwargs):
        await self.async_write(self._on_value)

    async def async_turn_off(self, **kwargs):
        await self.async_write(self._off_value)

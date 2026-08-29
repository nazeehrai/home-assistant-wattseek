from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import WattSeekEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WattSeekGroupSubmitButton(coordinator, group)
        for group in coordinator.iter_groups()
    )


class WattSeekGroupSubmitButton(WattSeekEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, group):
        self.group_id = str(group["groupId"])
        self.group_name = str(group.get("groupName") or self.group_id)
        super().__init__(coordinator, f"group_{self.group_id}_submit")
        self._attr_name = f"{self.group_name} — Submit"
        self._attr_icon = "mdi:upload"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.has_pending_changes(self.group_id)

    async def async_press(self) -> None:
        await self.coordinator.async_submit_group(self.group_id)

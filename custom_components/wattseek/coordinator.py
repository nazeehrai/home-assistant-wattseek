from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WattSeekApi, WattSeekApiError
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


def flatten_detail(detail: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for module in detail.get("attrModuleList", []) or []:
        for attr in module.get("attrList", []) or []:
            out[attr.get("attrName")] = attr.get("attrValue")
    return out


def flatten_values(groups: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for group in groups or []:
        for attr in group.get("attrList", []) or []:
            out[str(attr.get("cmdId"))] = attr.get("cmdValue")
    return out


class WattSeekCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: WattSeekApi, interval: int) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api
        self.protocol: dict[str, Any] = {}
        self.pending_values: dict[str, dict[str, Any]] = {}
        self._group_locks: dict[str, asyncio.Lock] = {}

    async def async_initialize(
        self,
        plant_id: str | None = None,
        device_id: str | None = None,
    ) -> None:
        await self.api.login()
        await self.api.discover(plant_id=plant_id, device_id=device_id)
        self.protocol = await self.api.get_protocol()
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            flow = await self.api.get_flow()
            detail = await self.api.get_detail()
            values = await self.api.get_command_values()
        except WattSeekApiError as err:
            raise UpdateFailed(str(err)) from err

        return {
            "flow": flow or {},
            "detail": detail or {},
            "detail_flat": flatten_detail(detail or {}),
            "command_values": flatten_values(values or []),
            "command_value_groups": values or [],
        }

    def iter_groups(self):
        yield from (self.protocol or {}).get("cmdGroupList", []) or []

    def group_definition(self, group_id: str) -> dict[str, Any]:
        for group in self.iter_groups():
            if str(group.get("groupId")) == str(group_id):
                return group
        raise WattSeekApiError(f"WattSeek command group {group_id} was not found")

    def group_name(self, group_id: str) -> str:
        group = self.group_definition(group_id)
        return str(group.get("groupName") or group_id)

    def confirmed_value(self, cmd_id: str) -> Any:
        return (self.data or {}).get("command_values", {}).get(str(cmd_id))

    def effective_command_values(self) -> dict[str, Any]:
        values = dict((self.data or {}).get("command_values", {}))
        for pending in self.pending_values.values():
            values.update(pending)
        return values

    def effective_value(self, group_id: str, cmd_id: str) -> Any:
        return self.pending_values.get(str(group_id), {}).get(
            str(cmd_id),
            self.confirmed_value(cmd_id),
        )

    def has_pending_changes(self, group_id: str) -> bool:
        return bool(self.pending_values.get(str(group_id)))

    @callback
    def stage_value(self, group_id: str, cmd_id: str, value: Any) -> None:
        group_id = str(group_id)
        cmd_id = str(cmd_id)
        if self._values_equal(value, self.confirmed_value(cmd_id)):
            pending = self.pending_values.get(group_id)
            if pending is not None:
                pending.pop(cmd_id, None)
                if not pending:
                    self.pending_values.pop(group_id, None)
        else:
            self.pending_values.setdefault(group_id, {})[cmd_id] = value
        self.async_update_listeners()

    async def async_submit_group(self, group_id: str) -> None:
        group_id = str(group_id)
        lock = self._group_locks.setdefault(group_id, asyncio.Lock())
        async with lock:
            pending = dict(self.pending_values.get(group_id, {}))
            if not pending:
                return

            current_values = flatten_values(await self.api.get_command_values())
            current_values.update(pending)
            cmd_list = self._build_group_command_list(group_id, current_values)

            # This exactly mirrors WattSeek's Set up transaction.
            await self.api.send_group_command(group_id, "WRITE", cmd_list)
            await self.api.send_group_command(group_id, "READ", cmd_list)

            # The portal reloads both endpoints after READ succeeds.
            await self.api.get_command_values()
            self.protocol = await self.api.get_protocol()
            await self.async_request_refresh()

            # Preserve any edits made while this transaction was running.
            current_pending = self.pending_values.get(group_id, {})
            for cmd_id, submitted_value in pending.items():
                if self._values_equal(current_pending.get(cmd_id), submitted_value):
                    current_pending.pop(cmd_id, None)
            if not current_pending:
                self.pending_values.pop(group_id, None)
            self.async_update_listeners()

    def _build_group_command_list(
        self,
        group_id: str,
        values: dict[str, Any],
    ) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        missing: list[str] = []
        group = self.group_definition(group_id)

        for command in group.get("cmdList", []) or []:
            command_id = str(command["cmdId"])
            if command_id not in values:
                missing.append(command_id)
                continue
            commands.append(
                {
                    "cmdId": command_id,
                    "cmdValue": values[command_id],
                }
            )

        if missing:
            raise WattSeekApiError(
                "Cannot submit WattSeek command group; missing current values for "
                + ", ".join(missing)
            )
        if not commands:
            raise WattSeekApiError(f"WattSeek command group {group_id} is empty")
        return commands

    @staticmethod
    def _values_equal(left: Any, right: Any) -> bool:
        if left is None or right is None:
            return left is right
        return str(left) == str(right)

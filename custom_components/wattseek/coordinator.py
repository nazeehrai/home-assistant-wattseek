from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WattSeekApi, WattSeekApiError
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)
WRITE_CONFIRM_ATTEMPTS = 6
WRITE_CONFIRM_INTERVAL = 2


def command_values_equal(actual: Any, expected: Any) -> bool:
    """Compare WattSeek values while tolerating equivalent numeric formats."""
    if str(actual) == str(expected):
        return True
    try:
        return Decimal(str(actual)) == Decimal(str(expected))
    except (InvalidOperation, TypeError, ValueError):
        return False


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

    async def async_initialize(self) -> None:
        await self.api.login()
        await self.api.discover()
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

    async def async_write_command(self, group_id: str, cmd_id: str, value: Any) -> None:
        await self.api.send_command(group_id, cmd_id, value)

        # WattSeek may acknowledge a write before the command-value endpoint
        # exposes it. Read the value back before refreshing Home Assistant so
        # entities do not briefly revert to their previous state.
        expected = str(value)
        for attempt in range(WRITE_CONFIRM_ATTEMPTS):
            values = flatten_values(await self.api.get_command_values())
            if command_values_equal(values.get(str(cmd_id)), expected):
                break
            if attempt < WRITE_CONFIRM_ATTEMPTS - 1:
                await asyncio.sleep(WRITE_CONFIRM_INTERVAL)
        else:
            _LOGGER.warning(
                "WattSeek command %s was accepted but readback did not confirm value %s",
                cmd_id,
                expected,
            )

        await self.async_request_refresh()

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WattSeekApi, WattSeekApiError
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)


class WattSeekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._api: WattSeekApi | None = None
        self._username = ""
        self._password = ""
        self._plants: dict[str, dict[str, Any]] = {}
        self._plant: dict[str, Any] | None = None
        self._inverters: dict[str, dict[str, Any]] = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._api = WattSeekApi(
                async_get_clientsession(self.hass),
                self._username,
                self._password,
            )
            try:
                await self._api.login()
                plants = await self._api.get_plants()
            except WattSeekApiError:
                errors["base"] = "cannot_connect"
            else:
                self._plants = {str(plant["plantId"]): plant for plant in plants}
                if not self._plants:
                    errors["base"] = "no_plants"
                elif len(self._plants) == 1:
                    self._plant = next(iter(self._plants.values()))
                    return await self.async_step_inverter()
                else:
                    return await self.async_step_plant()

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_plant(self, user_input=None):
        if user_input is not None:
            self._plant = self._plants[user_input[CONF_PLANT_ID]]
            return await self.async_step_inverter()

        choices = {
            plant_id: str(plant.get("plantName") or plant_id)
            for plant_id, plant in self._plants.items()
        }
        return self.async_show_form(
            step_id="plant",
            data_schema=vol.Schema(
                {vol.Required(CONF_PLANT_ID): vol.In(choices)}
            ),
        )

    async def async_step_inverter(self, user_input=None):
        if self._api is None or self._plant is None:
            return self.async_abort(reason="cannot_connect")

        if not self._inverters:
            try:
                devices = await self._api.get_devices(str(self._plant["plantId"]))
            except WattSeekApiError:
                return self.async_abort(reason="cannot_connect")
            self._inverters = {
                str(device["deviceId"]): device
                for device in devices
                if device.get("deviceType") == "INVERTER"
            }
            if not self._inverters:
                return self.async_abort(reason="no_inverters")

        if user_input is not None:
            device = self._inverters[user_input[CONF_DEVICE_ID]]
            device_id = str(device["deviceId"])
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            device_name = str(
                device.get("deviceName")
                or device.get("deviceModel")
                or device.get("deviceSn")
                or "WattSeek Inverter"
            )
            plant_name = str(
                self._plant.get("plantName") or self._plant["plantId"]
            )
            return self.async_create_entry(
                title=device_name,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_PLANT_ID: str(self._plant["plantId"]),
                    CONF_PLANT_NAME: plant_name,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                },
                options={CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
            )

        choices = {
            device_id: self._device_label(device)
            for device_id, device in self._inverters.items()
        }
        return self.async_show_form(
            step_id="inverter",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_ID): vol.In(choices)}
            ),
        )

    @staticmethod
    def _device_label(device: dict[str, Any]) -> str:
        name = device.get("deviceName") or "WattSeek Inverter"
        model = device.get("deviceModel")
        serial = device.get("deviceSn")
        details = " · ".join(str(value) for value in (model, serial) if value)
        return f"{name} ({details})" if details else str(name)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WattSeekOptionsFlow()


class WattSeekOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=current
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

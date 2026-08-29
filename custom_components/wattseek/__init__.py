from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WattSeekApi
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    DOMAIN,
    PLATFORMS,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .coordinator import WattSeekCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = WattSeekApi(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    interval = int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    coordinator = WattSeekCoordinator(hass, api, interval)
    await coordinator.async_initialize(
        plant_id=entry.data.get(CONF_PLANT_ID),
        device_id=entry.data.get(CONF_DEVICE_ID) or entry.unique_id,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    interval = int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    coordinator.update_interval = timedelta(seconds=interval)
    await coordinator.async_request_refresh()


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Add explicit plant and inverter selection to pre-0.3 entries."""
    if entry.version >= 2:
        return True

    api = WattSeekApi(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    try:
        await api.login()
        await api.discover(device_id=entry.unique_id)
    except Exception:
        return False

    plant = api.plant or {}
    device = api.device or {}
    data = {
        **entry.data,
        CONF_PLANT_ID: str(plant["plantId"]),
        CONF_PLANT_NAME: str(plant.get("plantName") or plant["plantId"]),
        CONF_DEVICE_ID: api.device_id,
        CONF_DEVICE_NAME: str(
            device.get("deviceName")
            or device.get("deviceModel")
            or device.get("deviceSn")
            or "WattSeek Inverter"
        ),
    }
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        unique_id=api.device_id,
        version=2,
    )
    return True

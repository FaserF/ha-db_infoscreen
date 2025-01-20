from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta
import aiohttp
import async_timeout
import logging

from .const import DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DEFAULT_NEXT_DEPARTURES, CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES

_LOGGER = logging.getLogger(__name__)

class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, station: str, next_departures: int, update_interval: int, hide_low_delay: bool, detailed: bool, past_60_minutes: bool):
        self.station = station
        self.next_departures = next_departures
        self.hide_low_delay = hide_low_delay
        self.detailed = detailed
        self.past_60_minutes = past_60_minutes
        
        # Construct the URL based on configuration
        url = f"https://dbf.finalrewind.org/{station}.json"
        if hide_low_delay:
            url += "?hidelowdelay=1"
        if detailed:
            url += "&detailed=1"
        if past_60_minutes:
            url += "&?past=1"

        self.api_url = url
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"DB Info Screen {station}",
            update_interval=timedelta(minutes=update_interval),
        )
        _LOGGER.debug(
            "Coordinator initialized for station %s with update interval %d minutes",
            station, update_interval
        )

    async def _async_update_data(self):
        _LOGGER.debug("Fetching data for station: %s", self.station)
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    response = await session.get(self.api_url)
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug("Data fetched successfully: %s", str(data)[:400] + ("..." if len(str(data)) > 400 else ""))
                    return data["departures"][:self.next_departures]
            except Exception as e:
                _LOGGER.error(
                    "Error fetching data for station %s: %s", self.station, str(e),
                    exc_info=True
                )
                return []  # Return empty list instead of raising an exception

async def async_setup_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    station = config_entry.data[CONF_STATION]
    next_departures = config_entry.data.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    hide_low_delay = config_entry.data.get(CONF_HIDE_LOW_DELAY, False)
    detailed = config_entry.data.get(CONF_DETAILED, False)
    past_60_minutes = config_entry.data.get(CONF_PAST_60_MINUTES, False)

    coordinator = DBInfoScreenCoordinator(hass, station, next_departures, update_interval, hide_low_delay, detailed, past_60_minutes)
    coordinator.update_interval = timedelta(minutes=update_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok

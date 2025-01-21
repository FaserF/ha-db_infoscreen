from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import logging

from .const import DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DEFAULT_NEXT_DEPARTURES, DEFAULT_OFFSET, CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES, CONF_CUSTOM_API_URL, CONF_DATA_SOURCE, CONF_OFFSET

_LOGGER = logging.getLogger(__name__)

class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, station: str, next_departures: int, update_interval: int, hide_low_delay: bool, detailed: bool, past_60_minutes: bool, custom_api_url: str, data_source: str, offset: str):
        self.station = station
        self.next_departures = next_departures
        self.hide_low_delay = hide_low_delay
        self.detailed = detailed
        self.past_60_minutes = past_60_minutes
        self.data_source = data_source
        self.offset = self.convert_offset_to_seconds(offset)
        
        if custom_api_url:
            url = f"{custom_api_url}/{station}.json"
        else:
            url = f"https://dbf.finalrewind.org/{station}.json"

        if data_source == "MVV":
            url += f"?efa=MVV" if "?" not in url else "&efa=MVV"
        elif data_source == "ÖBB":
            url += f"?hafas=ÖBB" if "?" not in url else "?hafas=ÖBB"

        if hide_low_delay:
            url += "?hidelowdelay=1" if "?" not in url else "&hidelowdelay=1"
        if detailed:
            url += "&detailed=1" if "?" in url else "?detailed=1"
        if past_60_minutes:
            url += "&past_60_minutes=1" if "?" in url else "?past_60_minutes=1"

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

    def convert_offset_to_seconds(self, offset: str) -> int:
        """
        Converts an offset string in HH:MM or HH:MM:SS format to seconds.
        """
        try:
            time_parts = list(map(int, offset.split(":")))
            if len(time_parts) == 2:  # HH:MM format
                return time_parts[0] * 3600 + time_parts[1] * 60
            elif len(time_parts) == 3:  # HH:MM:SS format
                return time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
            else:
                raise ValueError("Invalid time format")
        except ValueError:
            _LOGGER.error("Invalid offset format: %s", offset)
            return 0

    async def _async_update_data(self):
        _LOGGER.debug("Fetching data for station: %s", self.station)
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    response = await session.get(self.api_url)
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug("Data fetched successfully: %s", str(data)[:400] + ("..." if len(str(data)) > 400 else ""))

                    # Filter departures based on the offset
                    filtered_departures = []
                    for departure in data.get("departures", []):
                        departure_time = departure.get("scheduledDeparture")
                        if departure_time:
                            try:
                                departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                try:
                                    departure_time = datetime.strptime(departure_time, "%H:%M").replace(
                                        year=datetime.now().year,
                                        month=datetime.now().month,
                                        day=datetime.now().day,
                                    )
                                except ValueError:
                                    _LOGGER.error("Invalid time format: %s", departure_time)
                                    continue

                            departure_seconds = (departure_time - datetime.now()).total_seconds()
                            if departure_seconds >= self.offset:  # Only show departures after the offset
                                filtered_departures.append(departure)
                    
                    return filtered_departures[:self.next_departures]
            except Exception as e:
                _LOGGER.error(
                    "Error fetching data for station %s: %s", self.station, str(e),
                    exc_info=True
                )
                return []

async def async_setup_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    station = config_entry.data[CONF_STATION]
    next_departures = config_entry.data.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    hide_low_delay = config_entry.data.get(CONF_HIDE_LOW_DELAY, False)
    detailed = config_entry.data.get(CONF_DETAILED, False)
    past_60_minutes = config_entry.data.get(CONF_PAST_60_MINUTES, False)
    custom_api_url = config_entry.data.get(CONF_CUSTOM_API_URL, "")
    data_source = config_entry.data.get(CONF_DATA_SOURCE, "IRIS-TTS")
    offset = config_entry.data.get(CONF_OFFSET, DEFAULT_OFFSET)

    coordinator = DBInfoScreenCoordinator(
        hass, station, next_departures, update_interval, hide_low_delay,
        detailed, past_60_minutes, custom_api_url, data_source, offset
    )
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

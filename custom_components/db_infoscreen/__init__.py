from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import logging
from urllib.parse import quote

from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_OFFSET, CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES,
    CONF_CUSTOM_API_URL, CONF_DATA_SOURCE, CONF_OFFSET, CONF_PLATFORMS, CONF_ADMODE, MIN_UPDATE_INTERVAL,
    CONF_VIA_STATIONS, CONF_IGNORED_TRAINTYPES, CONF_DROP_LATE_TRAINS
)

_LOGGER = logging.getLogger(__name__)

class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, station: str, next_departures: int, update_interval: int, hide_low_delay: bool, detailed: bool, past_60_minutes: bool, custom_api_url: str, data_source: str, offset: str, platforms: str, admode: str, via_stations: list, ignored_train_types: list, drop_late_trains: bool):
        self.station = station
        self.next_departures = next_departures
        self.hide_low_delay = hide_low_delay
        self.detailed = detailed
        self.past_60_minutes = past_60_minutes
        self.data_source = data_source
        self.offset = self.convert_offset_to_seconds(offset)
        self.via_stations = via_stations
        self.ignored_train_types = ignored_train_types
        self.drop_late_trains = drop_late_trains

        station_cleaned = " ".join(station.split())
        encoded_station = quote(station_cleaned, safe=",-")
        encoded_station = encoded_station.replace(" ", "%20")

        # Build the API URL
        if custom_api_url:
            url = f"{custom_api_url}/{encoded_station}.json"
        else:
            url = f"https://dbf.finalrewind.org/{encoded_station}.json"

        if platforms:
            url += f"?platforms={platforms}" if "?" not in url else f"&platforms={platforms}"

        if admode == "arrival":
            url += "?admode=arr" if "?" not in url else "&admode=arr"
        elif admode == "departure":
            url += "?admode=dep" if "?" not in url else "&admode=dep"

        if data_source == "MVV":
            url += f"?efa=MVV" if "?" not in url else "&efa=MVV"
        elif data_source == "\u00d6BB":
            url += f"?hafas=\u00d6BB" if "?" not in url else "&hafas=\u00d6BB"
        elif data_source == "BSVG":
            url += f"?efa=BSVG" if "?" not in url else "&efa=BSVG"
        elif data_source == "DING":
            url += f"?efa=DING" if "?" not in url else "&efa=DING"
        elif data_source == "KVV":
            url += f"?efa=KVV" if "?" not in url else "&efa=KVV"
        elif data_source == "LinzAG":
            url += f"?efa=LinzAG" if "?" not in url else "&efa=LinzAG"
        elif data_source == "NVBW":
            url += f"?efa=NVBW" if "?" not in url else "&efa=NVBW"
        elif data_source == "NWL":
            url += f"?efa=NWL" if "?" not in url else "&efa=NWL"
        elif data_source == "VAG":
            url += f"?efa=VAG" if "?" not in url else "&efa=VAG"
        elif data_source == "VGN":
            url += f"?efa=VGN" if "?" not in url else "&efa=VGN"
        elif data_source == "VMV":
            url += f"?efa=VMV" if "?" not in url else "&efa=VMV"
        elif data_source == "VRN":
            url += f"?efa=VRN" if "?" not in url else "&efa=VRN"
        elif data_source == "VRN2":
            url += f"?hafas=VRN" if "?" not in url else "&hafas=VRN"
        elif data_source == "VRR":
            url += f"?efa=VRR" if "?" not in url else "&efa=VRR"
        elif data_source == "VRR2":
            url += f"?efa=VRR2" if "?" not in url else "&efa=VRR2"
        elif data_source == "VRR3":
            url += f"?efa=VRR3" if "?" not in url else "&efa=VRR3"
        elif data_source == "VVO":
            url += f"?efa=VVO" if "?" not in url else "&efa=VVO"
        elif data_source == "VVS":
            url += f"?efa=VVS" if "?" not in url else "&efa=VVS"
        elif data_source == "bwegt":
            url += f"?efa=bwegt" if "?" not in url else "&efa=bwegt"
        elif data_source == "AVV":
            url += f"?hafas=AVV" if "?" not in url else "&hafas=AVV"
        elif data_source == "BART":
            url += f"?hafas=BART" if "?" not in url else "&hafas=BART"
        elif data_source == "BLS":
            url += f"?hafas=BLS" if "?" not in url else "&hafas=BLS"
        elif data_source == "BVG":
            url += f"?hafas=BVG" if "?" not in url else "&hafas=BVG"
        elif data_source == "CMTA":
            url += f"?hafas=CMTA" if "?" not in url else "&hafas=CMTA"
        elif data_source == "DSB":
            url += f"?hafas=DSB" if "?" not in url else "&hafas=DSB"
        elif data_source == "IE":
            url += f"?hafas=IE" if "?" not in url else "&hafas=IE"
        elif data_source == "KVB":
            url += f"?hafas=KVB" if "?" not in url else "&hafas=KVB"
        elif data_source == "NAHSH":
            url += f"?hafas=NAHSH" if "?" not in url else "&hafas=NAHSH"
        elif data_source == "NVV":
            url += f"?hafas=NVV" if "?" not in url else "&hafas=NVV"
        elif data_source == "RMV":
            url += f"?hafas=RMV" if "?" not in url else "&hafas=RMV"
        elif data_source == "RSAG":
            url += f"?hafas=RSAG" if "?" not in url else "&hafas=RSAG"
        elif data_source == "Resrobot":
            url += f"?hafas=Resrobot" if "?" not in url else "&hafas=Resrobot"
        elif data_source == "STV":
            url += f"?hafas=STV" if "?" not in url else "&hafas=STV"
        elif data_source == "SaarVV":
            url += f"?hafas=SaarVV" if "?" not in url else "&hafas=SaarVV"
        elif data_source == "TPG":
            url += f"?hafas=TPG" if "?" not in url else "&hafas=TPG"
        elif data_source == "VBB":
            url += f"?hafas=VBB" if "?" not in url else "&hafas=VBB"
        elif data_source == "VBN":
            url += f"?hafas=VBN" if "?" not in url else "&hafas=VBN"
        elif data_source == "VMT":
            url += f"?hafas=VMT" if "?" not in url else "&hafas=VMT"
        elif data_source == "VOS":
            url += f"?hafas=VOS" if "?" not in url else "&hafas=VOS"
        elif data_source == "VRN":
            url += f"?hafas=VRN" if "?" not in url else "&hafas=VRN"
        elif data_source == "ZVV":
            url += f"?hafas=ZVV" if "?" not in url else "&hafas=ZVV"
        elif data_source == "mobiliteit":
            url += f"?hafas=mobiliteit" if "?" not in url else "&hafas=mobiliteit"
        elif data_source == "hafas=1":
            url += f"?hafas=1" if "?" not in url else "&hafas=1"

        if hide_low_delay:
            url += "?hidelowdelay=1" if "?" not in url else "&hidelowdelay=1"
        if detailed:
            url += "?detailed=1" if "?" not in url else "&detailed=1"
        if past_60_minutes:
            url += "?past=1" if "?" not in url else "&past=1"

        if via_stations:
            encoded_via_stations = [quote(station.strip(), safe=",-") for station in via_stations]
            via_param = ",".join(encoded_via_stations)
            url += f"?via={via_param}" if "?" not in url else f"&via={via_param}"

        self.api_url = url

        # Ensure update_interval is passed correctly
        update_interval = max(update_interval, MIN_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"DB Info {station}",
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
        """
        Fetches data from the API and processes it based on the configuration.
        """
        _LOGGER.debug("Fetching data for station: %s", self.station)
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    response = await session.get(self.api_url)
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug("Data fetched successfully: %s", str(data)[:350] + ("..." if len(str(data)) > 350 else ""))

                    # Set last_update timestamp
                    self.last_update = datetime.now()

                    # Filter departures based on the offset and ignored products
                    filtered_departures = []
                    ignored_train_types = self.ignored_train_types
                    if ignored_train_types:
                        _LOGGER.debug("Ignoring products: %s", ignored_train_types)

                    for departure in data.get("departures", []):
                        _LOGGER.debug("Processing departure: %s", departure)
                        # Handle different API response formats
                        scheduled_departure = departure.get("scheduledDeparture")
                        scheduled_time = departure.get("scheduledTime")

                        # Use the first available time field
                        departure_time = scheduled_departure or scheduled_time
                        if not departure_time:
                            _LOGGER.warning("No valid departure time found for entry: %s", departure)
                            continue

                        # Convert the time to a datetime object
                        if isinstance(departure_time, int):  # Unix timestamp case
                            departure_time = datetime.fromtimestamp(departure_time)
                        else:  # Assume ISO 8601 string
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

                        if not self.drop_late_trains:
                            _LOGGER.debug("Departure time without added delay: %s", departure_time)
                            delay_departure = departure.get("delayDeparture", 0)
                            departure_time += timedelta(minutes=delay_departure)
                            _LOGGER.debug("Departure time with added delay: %s", departure_time)

                        # Check if the train class is in the ignored products list
                        train_classes = departure.get("trainClasses", [])
                        _LOGGER.debug("Departure train classes: %s", train_classes)
                        if any(train_class in ignored_train_types for train_class in train_classes):
                            _LOGGER.debug("Ignoring departure due to train class: %s", train_classes)
                            continue

                        # Calculate time offset
                        departure_seconds = (departure_time - datetime.now()).total_seconds()
                        if departure_seconds >= self.offset:  # Only show departures after the offset
                            filtered_departures.append(departure)

                    return filtered_departures[:self.next_departures]
            except Exception as e:
                _LOGGER.error("Error fetching data: %s", e)
                return []

async def async_setup_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    station = config_entry.data[CONF_STATION]
    next_departures = config_entry.data.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)
    update_interval = max(config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)
    hide_low_delay = config_entry.data.get(CONF_HIDE_LOW_DELAY, False)
    detailed = config_entry.data.get(CONF_DETAILED, False)
    past_60_minutes = config_entry.data.get(CONF_PAST_60_MINUTES, False)
    custom_api_url = config_entry.data.get(CONF_CUSTOM_API_URL, "")
    data_source = config_entry.data.get(CONF_DATA_SOURCE, "IRIS-TTS")
    offset = config_entry.data.get(CONF_OFFSET, DEFAULT_OFFSET)
    platforms = config_entry.data.get(CONF_PLATFORMS, "")
    admode = config_entry.data.get(CONF_ADMODE, "")
    via_stations = config_entry.data.get(CONF_VIA_STATIONS, [])
    ignored_train_types = config_entry.data.get(CONF_IGNORED_TRAINTYPES, [])
    drop_late_trains = config_entry.data.get(CONF_DROP_LATE_TRAINS, [])

    coordinator = DBInfoScreenCoordinator(
        hass, station, next_departures, update_interval, hide_low_delay,
        detailed, past_60_minutes, custom_api_url, data_source, offset,
        platforms, admode, via_stations, ignored_train_types, drop_late_trains
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import logging
import json
from urllib.parse import quote_plus, urlencode

from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_OFFSET, CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES,
    CONF_CUSTOM_API_URL, CONF_DATA_SOURCE, CONF_OFFSET, CONF_PLATFORMS, CONF_ADMODE, MIN_UPDATE_INTERVAL,
    CONF_VIA_STATIONS, CONF_IGNORED_TRAINTYPES, CONF_DROP_LATE_TRAINS, CONF_KEEP_ROUTE
)

_LOGGER = logging.getLogger(__name__)

class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, station: str, next_departures: int, update_interval: int, hide_low_delay: bool, detailed: bool, past_60_minutes: bool, custom_api_url: str, data_source: str, offset: str, platforms: str, admode: str, via_stations: list, ignored_train_types: list, drop_late_trains: bool, keep_route: bool):
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
        self.keep_route = keep_route

        station_cleaned = " ".join(station.split())
        encoded_station = quote_plus(station_cleaned, safe=",-")
        encoded_station = encoded_station.replace(" ", "%20")

        base_url = custom_api_url if custom_api_url else "https://dbf.finalrewind.org"
        url = f"{base_url}/{encoded_station}.json"

        # Parameter mapping for data_source
        data_source_map = {
            "MVV": "efa=MVV", "ÖBB": "hafas=ÖBB", "BSVG": "efa=BSVG", "DING": "efa=DING",
            "KVV": "efa=KVV", "LinzAG": "efa=LinzAG", "NVBW": "efa=NVBW", "NWL": "efa=NWL",
            "VAG": "efa=VAG", "VGN": "efa=VGN", "VMV": "efa=VMV", "VRN": "efa=VRN",
            "VRN2": "hafas=VRN", "VRR": "efa=VRR", "VRR2": "efa=VRR2", "VRR3": "efa=VRR3",
            "VVO": "efa=VVO", "VVS": "efa=VVS", "bwegt": "efa=bwegt", "AVV": "hafas=AVV",
            "BART": "hafas=BART", "BLS": "hafas=BLS", "BVG": "hafas=BVG", "CMTA": "hafas=CMTA",
            "DSB": "hafas=DSB", "IE": "hafas=IE", "KVB": "hafas=KVB", "NAHSH": "hafas=NAHSH",
            "NVV": "hafas=NVV", "RMV": "hafas=RMV", "RSAG": "hafas=RSAG", "Resrobot": "hafas=Resrobot",
            "STV": "hafas=STV", "SaarVV": "hafas=SaarVV", "TPG": "hafas=TPG", "VBB": "hafas=VBB",
            "VBN": "hafas=VBN", "VMT": "hafas=VMT", "VOS": "hafas=VOS", "ZVV": "hafas=ZVV",
            "mobiliteit": "hafas=mobiliteit", "hafas=1": "hafas=1"
        }

        # Collect parameters
        params = {}
        if platforms:
            params["platforms"] = platforms
        if admode == "arrival":
            params["admode"] = "arr"
        elif admode == "departure":
            params["admode"] = "dep"
        if data_source in data_source_map:
            key, value = data_source_map[data_source].split("=")
            params[key] = value
        if hide_low_delay:
            params["hidelowdelay"] = "1"
        if detailed:
            params["detailed"] = "1"
        if past_60_minutes:
            params["past"] = "1"

        # Assemble URL
        query_string = urlencode(params)
        url = f"{url}?{query_string}" if query_string else url
        if via_stations:
            encoded_via_stations = [quote_plus(station.strip(), safe=",-") for station in via_stations]
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

                    MAX_SIZE_BYTES = 16000

                    for departure in data.get("departures", []):
                        _LOGGER.debug("Processing departure: %s", departure)
                        json_size = len(json.dumps(filtered_departures))
                        if json_size > MAX_SIZE_BYTES:
                            _LOGGER.info("Filtered departures JSON size exceeds limit: %d bytes for entry: %s . Ignoring some future departures to keep the size lower.", json_size, self.station)
                            break

                        # Get the scheduled departure and scheduled time
                        scheduled_departure = departure.get("scheduledDeparture")
                        scheduled_time = departure.get("scheduledTime")

                        # Use scheduledArrival if scheduledDeparture is None or empty
                        departure_time = scheduled_departure or departure.get("scheduledArrival") or scheduled_time

                        # If no valid departure time is found, log a warning and continue to the next departure
                        if not departure_time:
                            _LOGGER.warning("No valid departure time found for entry: %s", departure)
                            continue

                        # Convert the departure time to a datetime object
                        if isinstance(departure_time, int):  # Unix timestamp case
                            departure_time = datetime.fromtimestamp(departure_time)
                        else:  # ISO 8601 string case
                            try:
                                departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                try:
                                    # Fallback to assuming time format HH:MM if the previous format doesn't work
                                    departure_time = datetime.strptime(departure_time, "%H:%M").replace(
                                        year=datetime.now().year,
                                        month=datetime.now().month,
                                        day=datetime.now().day,
                                    )
                                except ValueError:
                                    _LOGGER.error("Invalid time format: %s", departure_time)
                                    continue

                        # Apply any delay to the departure time, if applicable
                        if not self.drop_late_trains:
                            _LOGGER.debug("Departure time without added delay: %s", departure_time)
                            delay_departure = departure.get("delayDeparture")
                            if delay_departure is None:
                                delay_departure = 0  # Set default value if None
                            departure_time += timedelta(minutes=delay_departure)
                            _LOGGER.debug("Departure time with added delay: %s", departure_time)

                        # Check if the train class is in the ignored list
                        train_classes = departure.get("trainClasses", [])
                        if any(train_class in ignored_train_types for train_class in train_classes):
                            _LOGGER.debug("Ignoring departure due to train class: %s", train_classes)
                            continue

                        if not self.keep_route:
                            _LOGGER.debug("Removing route attributes because keep_route is False")
                            departure.pop("route", None)
                            departure.pop("via", None)
                        else:
                            _LOGGER.debug("Keeping route attributes")

                        # Calculate the time offset and only add departures that occur after the offset
                        departure_seconds = (departure_time - datetime.now()).total_seconds()
                        if departure_seconds >= self.offset:  # Only show departures after the offset
                            filtered_departures.append(departure)

                    _LOGGER.debug("Number of departures added to the filtered list: %d", len(filtered_departures))
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
    keep_route = config_entry.data.get(CONF_KEEP_ROUTE, False)

    coordinator = DBInfoScreenCoordinator(
        hass, station, next_departures, update_interval, hide_low_delay,
        detailed, past_60_minutes, custom_api_url, data_source, offset,
        platforms, admode, via_stations, ignored_train_types, drop_late_trains, keep_route
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
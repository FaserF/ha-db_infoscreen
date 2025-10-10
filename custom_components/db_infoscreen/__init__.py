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
    CONF_VIA_STATIONS, CONF_DIRECTION, CONF_IGNORED_TRAINTYPES, CONF_DROP_LATE_TRAINS, CONF_KEEP_ROUTE, CONF_KEEP_ENDSTATION
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    # Set up the coordinator
    coordinator = DBInfoScreenCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # Set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"])

    # Add an update listener for options
    config_entry.add_update_listener(update_listener)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
        """
        Initialize the coordinator for a station: configure runtime options, build the API URL, and start the DataUpdateCoordinator.
        
        This constructor reads configuration and options from the provided config entry and sets up coordinator state used when fetching departures. It assigns attributes such as `station`, `next_departures`, `hide_low_delay`, `detailed`, `past_60_minutes`, `data_source`, `offset`, `via_stations`, `direction`, `ignored_train_types`, `drop_late_trains`, `keep_route`, `keep_endstation`, and `api_url`. It also determines the update interval, encodes the station and optional via stations for the API endpoint, maps the chosen data source to API query parameters, and initializes the base DataUpdateCoordinator with a name and update interval.
        """
        self.config_entry = config_entry

        # Get config from data and options
        config = {**config_entry.data, **config_entry.options}

        self.station = config[CONF_STATION]
        self.next_departures = config.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)
        self.hide_low_delay = config.get(CONF_HIDE_LOW_DELAY, False)
        self.detailed = config.get(CONF_DETAILED, False)
        self.past_60_minutes = config.get(CONF_PAST_60_MINUTES, False)
        self.data_source = config.get(CONF_DATA_SOURCE, "IRIS-TTS")
        self.offset = self.convert_offset_to_seconds(config.get(CONF_OFFSET, DEFAULT_OFFSET))
        self.via_stations = config.get(CONF_VIA_STATIONS, [])
        self.direction = config.get(CONF_DIRECTION, "")
        self.ignored_train_types = config.get(CONF_IGNORED_TRAINTYPES, [])
        self.drop_late_trains = config.get(CONF_DROP_LATE_TRAINS, False)
        self.keep_route = config.get(CONF_KEEP_ROUTE, False)
        self.keep_endstation = config.get(CONF_KEEP_ENDSTATION, False)
        custom_api_url = config.get(CONF_CUSTOM_API_URL, "")
        platforms = config.get(CONF_PLATFORMS, "")
        admode = config.get(CONF_ADMODE, "")
        update_interval = max(config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)

        station_cleaned = " ".join(self.station.split())
        encoded_station = quote_plus(station_cleaned, safe=",-").replace("+", "%20").replace(" ", "%20")

        base_url = custom_api_url if custom_api_url else "https://dbf.finalrewind.org"
        url = f"{base_url}/{encoded_station}.json"

        # Parameter mapping for data_source
        data_source_map = {
            "MVV": "efa=MVV", "ÖBB": "hafas=ÖBB", "BSVG": "efa=BSVG", "DING": "efa=DING",
            "KVV": "efa=KVV", "LinzAG": "efa=LinzAG", "NVBW": "efa=NVBW", "NWL": "efa=NWL",
            "VAG": "efa=VAG", "VGN": "efa=VGN", "VMV": "efa=VMV", "VRN": "efa=VRN",
            "VRN2": "hafas=VRN", "VRR": "efa=VRR", "VRR2": "efa=VRR2", "VRR3": "efa=VRR3",
            "VVO": "efa=VVO", "VVS": "efa=VVS", "bwegt": "efa=bwegt", "AVV": "hafas=AVV", "AVV (Aachen)": "hafas=AVV",
            "AVV (Augsburg)": "efa=AVV", "BART": "hafas=BART", "BLS": "hafas=BLS", "BVG": "hafas=BVG",
            "CMTA": "hafas=CMTA", "DSB": "hafas=DSB", "IE": "hafas=IE", "KVB": "hafas=KVB",
            "NAHSH": "hafas=NAHSH", "NVV": "hafas=NVV", "RMV": "hafas=RMV", "Resrobot": "hafas=Resrobot",
            "RSAG": "hafas=RSAG", "SaarVV": "hafas=SaarVV", "STV": "hafas=STV", "TPG": "hafas=TPG",
            "VBB": "hafas=VBB", "VBN": "hafas=VBN", "VMT": "hafas=VMT", "VOS": "hafas=VOS",
            "ZVV": "hafas=ZVV", "mobiliteit": "hafas=mobiliteit", "hafas=1": "hafas=1", "PKP": "hafas=PKP",
            "VMV": "efa=VMV", "NASA": "hafas=NASA", "BEG": "efa=BEG", "Rolph": "efa=Rolph"
        }

        # Collect parameters
        params = {}
        if platforms:
            params["platforms"] = platforms
        if admode == "arrival":
            params["admode"] = "arr"
        elif admode == "departure":
            params["admode"] = "dep"

        # Check if the data source is in the HAFAS list
        if self.data_source in data_source_map:
            key, value = data_source_map[self.data_source].split("=")
            params[key] = value

        if self.hide_low_delay:
            params["hidelowdelay"] = "1"
        if self.detailed:
            params["detailed"] = "1"
        if self.past_60_minutes:
            params["past"] = "1"

        # Assemble URL
        query_string = urlencode(params)
        url = f"{url}?{query_string}" if query_string else url
        if self.via_stations:
            encoded_via_stations = [quote_plus(station.strip(), safe=",-") for station in self.via_stations]
            via_param = ",".join(encoded_via_stations)
            url += f"?via={via_param}" if "?" not in url else f"&via={via_param}"
        self.api_url = url

        super().__init__(
            hass,
            _LOGGER,
            name=f"DB Info {self.station}",
            update_interval=timedelta(minutes=update_interval),
        )
        self._last_valid_value = None
        _LOGGER.debug(
            "Coordinator initialized for station %s with update interval %d minutes",
            self.station, update_interval
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
        Fetch and return the next departures for the configured station, applying configured filters and transformations.
        
        Fetches JSON from the coordinator's API URL, processes the "departures" entries applying configured filters (direction, ignored train types, offset, final-stop exclusion, size limits), adjusts times and delay fields, optionally prunes route/details to reduce payload, and caches the most recent valid result for fallback when no valid departures are available.
        
        Returns:
            list[dict]: A list of processed departure objects limited to the configured `next_departures` count. If no valid departures can be produced, returns the last cached valid list or an empty list.
        """
        _LOGGER.debug("Fetching data for station: %s", self.station)
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    response = await session.get(self.api_url)
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("departures", []) is None:
                        _LOGGER.warning("Encountered empty departures list, skipping.")
                        return self._last_valid_value or []
                    _LOGGER.debug("Data fetched successfully: %s", str(data)[:350] + ("..." if len(str(data)) > 350 else ""))

                    # Set last_update timestamp
                    self.last_update = datetime.now()

                    # Filter departures based on the offset and ignored products
                    filtered_departures = []
                    ignored_train_types = self.ignored_train_types
                    if ignored_train_types:
                        if "S" in ignored_train_types and "S-Bahn" not in ignored_train_types:
                            ignored_train_types.append("S-Bahn")
                        if "StadtBus" in ignored_train_types and "MetroBus" not in ignored_train_types:
                            ignored_train_types.append("MetroBus")
                        _LOGGER.debug("Ignoring products: %s", ignored_train_types)

                    MAX_SIZE_BYTES = 16000

                    for departure in data.get("departures", []):
                        if departure is None:
                            _LOGGER.warning("Encountered None in departures list, skipping.")
                            continue
                        _LOGGER.debug("Processing departure: %s", departure)

                        # Direction filter
                        if self.direction:
                            departure_direction = departure.get("direction")
                            if not departure_direction or self.direction.lower() not in departure_direction.lower():
                                _LOGGER.debug(
                                    "Skipping departure due to direction mismatch. Required: '%s', actual: '%s'",
                                    self.direction,
                                    departure_direction,
                                )
                                continue

                        json_size = len(json.dumps(filtered_departures))
                        if json_size > MAX_SIZE_BYTES:
                            _LOGGER.info("Filtered departures JSON size exceeds limit: %d bytes for entry: %s . Ignoring some future departures to keep the size lower.", json_size, self.station)
                            break

                        if not self.keep_endstation:
                            if departure.get("destination") == self.station:
                                _LOGGER.debug("Skipping departure as %s is the final stop.", self.station)
                                continue

                        # Check if the train class is in the ignored list
                        trainClasses = departure.get("trainClasses")
                        train_classes = trainClasses or departure.get("train_type") or departure.get("type", [])
                        if train_classes:
                            if trainClasses:
                                train_type_mapping = {
                                    "S": "S-Bahn",
                                    "N": "Regionalbahn (DB)",
                                    "D": "Regionalbahn",
                                    "F": "Intercity (Express) / Eurocity",
                                    "": "Internationale Bahn"
                                }
                                updated_train_classes = [
                                    train_type_mapping.get(train_class, train_class) for train_class in train_classes
                                ]
                                departure["trainClasses"] = updated_train_classes
                                train_classes = updated_train_classes
                            if any(train_class in ignored_train_types for train_class in train_classes):
                                _LOGGER.debug("Ignoring departure due to train class: %s", train_classes)
                                continue

                        # Use scheduledArrival if scheduledDeparture is None or empty
                        departure_time = departure.get("scheduledDeparture") or departure.get("sched_dep") or departure.get("scheduledArrival") or departure.get("sched_arr") or departure.get("scheduledTime") or departure.get("dep") or departure.get("datetime")

                        # If no valid departure time is found, log a warning and continue to the next departure
                        if not departure_time:
                            _LOGGER.warning("No valid departure time found for entry: %s", departure)
                            continue

                        # Convert the departure time to a datetime object
                        if isinstance(departure_time, int):  # Unix timestamp case
                            departure_time = datetime.fromtimestamp(departure_time)
                        else:  # ISO 8601 string case
                            try:
                                # Try ISO with seconds first
                                departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                try:
                                    # Try ISO without seconds
                                    departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M")
                                except ValueError:
                                    try:
                                        # Fallback to HH:MM and roll over to next day if needed
                                        now = datetime.now()
                                        departure_time_candidate = datetime.strptime(departure_time, "%H:%M").replace(
                                            year=now.year,
                                            month=now.month,
                                            day=now.day,
                                        )
                                        if departure_time_candidate < now:
                                            departure_time_candidate = departure_time_candidate + timedelta(days=1)
                                        departure_time = departure_time_candidate
                                    except ValueError:
                                        _LOGGER.error("Invalid time format: %s", departure_time)
                                        continue

                        delay_departure = departure.get("delayDeparture") or departure.get("dep_delay") or departure.get("delay")
                        if delay_departure is None:
                            delay_departure = 0
                        else:
                            delay_departure = int(delay_departure)

                        if departure_time not in (None, "") and delay_departure is not None:
                            try:
                                departure_time_adjusted = departure_time + timedelta(minutes=delay_departure)
                                _LOGGER.debug("departure_current with added delay: %s", departure_time_adjusted)

                                if departure_time_adjusted.date() == datetime.now().date():
                                    departure["departure_current"] = departure_time_adjusted.strftime("%H:%M")
                                else:
                                    departure["departure_current"] = departure_time_adjusted.strftime("%Y-%m-%dT%H:%M")

                            except ValueError:
                                _LOGGER.error("Invalid time format for scheduledDeparture: %s", departure_time)
                        elif delay_departure is None:
                            _LOGGER.debug("No delay attribute found. Setting departure_current to departure_time: %s", departure_time)
                            if departure_time.date() == datetime.now().date():
                                departure["departure_current"] = departure_time.strftime("%H:%M")
                            else:
                                departure["departure_current"] = departure_time.strftime("%Y-%m-%dT%H:%M")
                        else:
                            _LOGGER.debug("No valid departure_time found. Setting departure_current to None.")
                            departure["departure_current"] = None

                        scheduled_arrival = departure.get("scheduledArrival")
                        delay_arrival = departure.get("delayArrival")
                        if delay_arrival is None:
                            delay_arrival = 0

                        if scheduled_arrival not in (None, "") and delay_arrival is not None:
                            try:
                                if "T" in scheduled_arrival:
                                    arrival_time = datetime.strptime(scheduled_arrival, "%Y-%m-%dT%H:%M")
                                else:
                                    now = datetime.now()
                                    arrival_time = datetime.strptime(scheduled_arrival, "%H:%M").replace(
                                        year=now.year, month=now.month, day=now.day
                                    )

                                arrival_time_adjusted = arrival_time + timedelta(minutes=delay_arrival)
                                _LOGGER.debug("arrival_current with added delay: %s", arrival_time_adjusted)

                                if arrival_time_adjusted.date() == datetime.now().date():
                                    departure["arrival_current"] = arrival_time_adjusted.strftime("%H:%M")
                                else:
                                    departure["arrival_current"] = arrival_time_adjusted.strftime("%Y-%m-%dT%H:%M")

                            except ValueError:
                                _LOGGER.error("Invalid time format for scheduledArrival: %s", scheduled_arrival)
                        elif delay_arrival is None:
                            _LOGGER.debug("No delay attribute found. Setting arrival_current to scheduledArrival: %s", scheduled_arrival)
                            if scheduled_arrival.date() == datetime.now().date():
                                departure["arrival_current"] = scheduled_arrival.strftime("%H:%M")
                            else:
                                departure["arrival_current"] = scheduled_arrival.strftime("%Y-%m-%dT%H:%M")
                        else:
                            if not delay_arrival is None:
                                _LOGGER.debug("No valid scheduledArrival found. Setting arrival_current to departure_current.")
                                departure["arrival_current"] = departure.get("departure_current")
                            else:
                                _LOGGER.debug("No valid scheduledArrival found. Setting arrival_current to None.")
                                departure["arrival_current"] = None

                        if not self.drop_late_trains:
                            departure_time += timedelta(minutes=delay_departure or 0)

                        # Apply any delay to the departure time, if applicable
                        if not self.drop_late_trains:
                            _LOGGER.debug("Departure time without added delay: %s", departure_time)
                            if delay_departure is None:
                                delay_departure = 0  # Set delay to 0 as fallback if no valid delay has been found
                            departure_time += timedelta(minutes=delay_departure)
                            _LOGGER.debug("Departure time with added delay: %s", departure_time)

                        # Remove route attributes to lower sensor size limit: https://github.com/FaserF/ha-db_infoscreen/issues/22
                        if not self.detailed:
                            departure.pop("id", None)
                            departure.pop("stop_id_num", None)
                            departure.pop("stateless", None)
                            departure.pop("key", None)
                            departure.pop("messages", None)
                            departure.pop("mot", None)

                            # Remove attributes with None or empty string – except for allowed keys
                            allowed_null_keys = {
                                "scheduledDeparture", "scheduledTime", "delay", "delayDeparture",
                                "scheduledArrival", "arrival_current", "departure_current",
                                "sched_dep", "sched_arr", "dep", "datetime"
                            }

                            keys_to_remove = [
                                key for key, value in departure.items()
                                if (value is None or (isinstance(value, str) and value.strip() == "")) and key not in allowed_null_keys
                            ]

                            for key in keys_to_remove:
                                departure.pop(key)

                        if not self.keep_route:
                            _LOGGER.debug("Removing route attributes because keep_route is False")
                            departure.pop("route", None)
                            departure.pop("via", None)
                            departure.pop("prev_route", None)
                            departure.pop("next_route", None)
                        else:
                            _LOGGER.debug("Keeping route attributes")

                        # Calculate the time offset and only add departures that occur after the offset
                        departure_seconds = (departure_time - datetime.now()).total_seconds()
                        if departure_seconds >= self.offset:  # Only show departures after the offset
                            filtered_departures.append(departure)

                    _LOGGER.debug("Number of departures added to the filtered list: %d", len(filtered_departures))
                    if filtered_departures:
                        self._last_valid_value = filtered_departures[:self.next_departures]
                        _LOGGER.debug("Fetched and cached %d valid departures", len(filtered_departures))
                        return filtered_departures[:self.next_departures]
                    else:
                        _LOGGER.warning("Departures fetched but all were filtered out. Using cached data.")
                        return self._last_valid_value or []
            except Exception as e:
                _LOGGER.error("Error fetching data: %s", e)
                _LOGGER.info("Trying to use last valid data: %s", e)
                return self._last_valid_value or []
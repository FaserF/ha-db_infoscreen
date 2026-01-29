from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import asyncio
import logging
import json
import re
from urllib.parse import quote, urlencode

from .const import (
    DOMAIN,
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES,
    DEFAULT_OFFSET,
    CONF_HIDE_LOW_DELAY,
    CONF_DETAILED,
    CONF_PAST_60_MINUTES,
    CONF_CUSTOM_API_URL,
    CONF_DATA_SOURCE,
    CONF_OFFSET,
    CONF_PLATFORMS,
    CONF_ADMODE,
    MIN_UPDATE_INTERVAL,
    CONF_VIA_STATIONS,
    CONF_DIRECTION,
    CONF_EXCLUDED_DIRECTIONS,
    CONF_IGNORED_TRAINTYPES,
    CONF_DROP_LATE_TRAINS,
    CONF_KEEP_ROUTE,
    CONF_KEEP_ENDSTATION,
    CONF_DEDUPLICATE_DEPARTURES,
    TRAIN_TYPE_MAPPING,
    CONF_EXCLUDE_CANCELLED,
    CONF_SHOW_OCCUPANCY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
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


async def async_unload_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, "sensor"
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def update_listener(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class DBInfoScreenCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
        """
        Initialize coordinator state from a config entry, build the API endpoint, and configure the DataUpdateCoordinator.

        Reads runtime configuration and options from the provided config entry to set coordinator attributes (for example: station, next_departures, hide_low_delay, detailed, past_60_minutes, data_source, offset, via_stations, direction, ignored_train_types, drop_late_trains, final-stop exclusion, size limits), adjusts departure/arrival times for delays, and prunes detail fields according to configuration. The most recent valid result is cached and used as a fallback when no valid departures can be produced.

        Parameters:
            hass (HomeAssistant): Home Assistant core instance.
            config_entry (config_entries.ConfigEntry): Integration config entry providing `data` and `options` used to configure the coordinator.
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
        self.offset = self.convert_offset_to_seconds(
            config.get(CONF_OFFSET, DEFAULT_OFFSET)
        )
        self.via_stations = config.get(CONF_VIA_STATIONS, [])
        self.direction = config.get(CONF_DIRECTION, "")
        self.excluded_directions = config.get(CONF_EXCLUDED_DIRECTIONS, "")
        self.ignored_train_types = config.get(CONF_IGNORED_TRAINTYPES, [])
        self.drop_late_trains = config.get(CONF_DROP_LATE_TRAINS, False)
        self.keep_route = config.get(CONF_KEEP_ROUTE, False)
        self.keep_endstation = config.get(CONF_KEEP_ENDSTATION, False)
        self.deduplicate_departures = config.get(CONF_DEDUPLICATE_DEPARTURES, False)
        self.exclude_cancelled = config.get(CONF_EXCLUDE_CANCELLED, False)
        self.show_occupancy = config.get(CONF_SHOW_OCCUPANCY, False)
        custom_api_url = config.get(CONF_CUSTOM_API_URL, "")
        platforms = config.get(CONF_PLATFORMS, "")
        admode = config.get(CONF_ADMODE, "")
        update_interval = max(
            config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            MIN_UPDATE_INTERVAL,
        )

        station_cleaned = " ".join(self.station.split())
        encoded_station = quote(station_cleaned, safe=",-")

        base_url = custom_api_url if custom_api_url else "https://dbf.finalrewind.org"
        url = f"{base_url}/{encoded_station}.json"

        # Parameter mapping for data_source
        data_source_map = {
            "MVV": "efa=MVV",
            "ÖBB": "hafas=ÖBB",
            "BSVG": "efa=BSVG",
            "DING": "efa=DING",
            "KVV": "efa=KVV",
            "LinzAG": "efa=LinzAG",
            "NVBW": "efa=NVBW",
            "NWL": "efa=NWL",
            "VAG": "efa=VAG",
            "VGN": "efa=VGN",
            "VMV": "efa=VMV",
            "VRN": "efa=VRN",
            "VRN2": "hafas=VRN",
            "VRR": "efa=VRR",
            "VRR2": "efa=VRR2",
            "VRR3": "efa=VRR3",
            "VVO": "efa=VVO",
            "VVS": "efa=VVS",
            "bwegt": "efa=bwegt",
            "AVV": "hafas=AVV",
            "AVV (Aachen)": "hafas=AVV",
            "AVV (Augsburg)": "efa=AVV",
            "BART": "hafas=BART",
            "BLS": "hafas=BLS",
            "BVG": "hafas=BVG",
            "CMTA": "hafas=CMTA",
            "DSB": "hafas=DSB",
            "IE": "hafas=IE",
            "KVB": "hafas=KVB",
            "NAHSH": "hafas=NAHSH",
            "NVV": "hafas=NVV",
            "RMV": "hafas=RMV",
            "Resrobot": "hafas=Resrobot",
            "RSAG": "hafas=RSAG",
            "SaarVV": "hafas=SaarVV",
            "STV": "hafas=STV",
            "TPG": "hafas=TPG",
            "VBB": "hafas=VBB",
            "VBN": "hafas=VBN",
            "VMT": "hafas=VMT",
            "VOS": "hafas=VOS",
            "ZVV": "hafas=ZVV",
            "mobiliteit": "hafas=mobiliteit",
            "hafas=1": "hafas=1",
            "PKP": "hafas=PKP",
            "NASA": "hafas=NASA",
            "BEG": "efa=BEG",
            "Rolph": "efa=Rolph",
            "RVV": "efa=RVV",
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
            encoded_via_stations = [
                quote(station.strip()) for station in self.via_stations
            ]
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
            self.station,
            update_interval,
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
        Retrieve and process next departures for the configured station.

        Fetches JSON from the coordinator's API, parses and normalizes departure times, optionally deduplicates entries, applies configured filters (direction, ignored train types, offset, final-stop exclusion, size limits), adjusts departure/arrival times for delays, and prunes detail fields according to configuration. The most recent valid result is cached and used as a fallback when no valid departures can be produced.

        Returns:
            list[dict]: Processed departure objects limited to the configured `next_departures` count. If no valid departures can be produced, returns the last cached valid list or an empty list.
        """
        _LOGGER.debug("Fetching data for station: %s", self.station)
        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    async with session.get(self.api_url) as response:
                        response.raise_for_status()
                        data = await response.json()

                    raw_departures = data.get("departures", [])
                    if raw_departures is None:
                        _LOGGER.warning("Encountered empty departures list, skipping.")
                        return self._last_valid_value or []

                    _LOGGER.debug(
                        "Data fetched successfully: %s",
                        str(data)[:350] + ("..." if len(str(data)) > 350 else ""),
                    )

                    # Set last_update timestamp
                    now = dt_util.now()
                    today = now.date()
                    self.last_update = now

                    # --- PRE-PROCESSING: Parse time for all departures ---
                    departures_with_time = []
                    for departure in raw_departures:
                        if departure is None:
                            continue

                        departure_time_str = (
                            departure.get("scheduledDeparture")
                            or departure.get("sched_dep")
                            or departure.get("scheduledArrival")
                            or departure.get("sched_arr")
                            or departure.get("scheduledTime")
                            or departure.get("dep")
                            or departure.get("datetime")
                        )

                        if not departure_time_str:
                            _LOGGER.warning(
                                "No valid departure time found for entry, skipping: %s",
                                departure,
                            )
                            continue

                        if isinstance(departure_time_str, (int, float)):
                            departure_time_obj = dt_util.utc_from_timestamp(
                                int(departure_time_str)
                            ).astimezone(now.tzinfo)
                        else:
                            # Attempt robust parsing using HA helper
                            parsed_dt = dt_util.parse_datetime(departure_time_str)
                            if parsed_dt:
                                if parsed_dt.tzinfo is None:
                                    departure_time_obj = now.replace(
                                        year=parsed_dt.year,
                                        month=parsed_dt.month,
                                        day=parsed_dt.day,
                                        hour=parsed_dt.hour,
                                        minute=parsed_dt.minute,
                                        second=parsed_dt.second,
                                        microsecond=parsed_dt.microsecond,
                                    )
                                    # Use a 5-minute grace window to handle next-day rollover
                                    if departure_time_obj < now - timedelta(minutes=5):
                                        departure_time_obj += timedelta(days=1)
                                else:
                                    departure_time_obj = parsed_dt.astimezone(
                                        now.tzinfo
                                    )
                            else:
                                # Fallback for HH:MM format (assume today)
                                try:
                                    temp_dt = datetime.strptime(
                                        departure_time_str, "%H:%M"
                                    )
                                    departure_time_obj = now.replace(
                                        hour=temp_dt.hour,
                                        minute=temp_dt.minute,
                                        second=0,
                                        microsecond=0,
                                    )
                                    if departure_time_obj < now - timedelta(
                                        minutes=5
                                    ):  # Allow for slight past times
                                        departure_time_obj += timedelta(days=1)
                                except (ValueError, TypeError):
                                    _LOGGER.error(
                                        "Invalid time format, skipping departure: %s",
                                        departure_time_str,
                                    )
                                    continue

                        # Excluded Direction filter
                        if self.excluded_directions:
                            departure_direction = departure.get("direction")
                            if (
                                departure_direction
                                and self.excluded_directions.lower()
                                in departure_direction.lower()
                            ):
                                _LOGGER.debug(
                                    "Skipping departure due to excluded direction match. Excluded: '%s', actual: '%s'",
                                    self.excluded_directions,
                                    departure_direction,
                                )
                                continue

                        departure["departure_datetime"] = departure_time_obj
                        departures_with_time.append(departure)

                    departures_to_process = departures_with_time

                    # --- DEDUPLICATION STEP ---
                    if self.deduplicate_departures:
                        _LOGGER.debug(
                            "Deduplication is enabled. Processing departures."
                        )
                        unique_departures = {}

                        departures_to_process.sort(
                            key=lambda d: d["departure_datetime"]
                        )

                        for departure in departures_to_process:
                            # Use a robust key for identifying a trip
                            key_line = departure.get("line") or departure.get("train")
                            key_dest = departure.get("destination")
                            # The 'key' field seems to be a reliable trip identifier in some sources (like KVV)
                            key_trip_id = departure.get("key") or departure.get(
                                "trainNumber"
                            )

                            # If we don't have enough info to build a key, treat it as unique.
                            if not key_line or not key_dest:
                                unique_departures[id(departure)] = departure
                                continue

                            # Build the key. Use trip ID if available, otherwise just line+dest
                            unique_key = (
                                (key_line, key_dest, key_trip_id)
                                if key_trip_id
                                else (key_line, key_dest)
                            )

                            # Check if we have already seen a departure for this trip
                            if unique_key not in unique_departures:
                                unique_departures[unique_key] = departure
                            else:
                                # We have seen this trip. Check the time difference.
                                existing_departure = unique_departures[unique_key]
                                time_diff = (
                                    departure["departure_datetime"]
                                    - existing_departure["departure_datetime"]
                                ).total_seconds()

                                # If the new one is within 2 minutes, it's a duplicate. We keep the earlier one.
                                if abs(time_diff) <= 120:
                                    _LOGGER.debug(
                                        "Found and filtering out duplicate departure. "
                                        "Keeping (earlier): %s, Removing (later): %s",
                                        existing_departure,
                                        departure,
                                    )
                                    # Since the list is sorted, the existing one is always earlier.
                                    # We do nothing and let the later one be discarded.
                                else:
                                    # Time difference is too large. This is a different trip that happens to share
                                    # the same line and destination. Add it with a more specific key to keep it.
                                    unique_departures[
                                        (unique_key, departure["departure_datetime"])
                                    ] = departure

                        departures_to_process = list(unique_departures.values())
                        # Re-sort because dictionary values don't guarantee order if we added time-suffixed keys
                        departures_to_process.sort(
                            key=lambda d: d["departure_datetime"]
                        )

                    # --- MAIN FILTERING AND PROCESSING ---
                    filtered_departures = []

                    # Map the configured ignored train types to the normalized values for correct comparison.
                    # e.g., if config is ['S'], this becomes {'S-Bahn'}.
                    ignored_train_types = self.ignored_train_types
                    mapped_ignored_train_types = {
                        TRAIN_TYPE_MAPPING.get(t, t) for t in ignored_train_types
                    }

                    # Some data sources might use other values, ensure compatibility.
                    if "S" in ignored_train_types:
                        mapped_ignored_train_types.add("S-Bahn")
                    if "StadtBus" in ignored_train_types:
                        mapped_ignored_train_types.add("MetroBus")

                    if mapped_ignored_train_types:
                        _LOGGER.debug(
                            "Ignoring train types (mapped): %s",
                            mapped_ignored_train_types,
                        )

                    MAX_SIZE_BYTES = 16000

                    for departure in departures_to_process:
                        _LOGGER.debug("Processing departure: %s", departure)

                        # Direction filter
                        if self.direction:
                            departure_direction = departure.get("direction")
                            if (
                                not departure_direction
                                or self.direction.lower()
                                not in departure_direction.lower()
                            ):
                                _LOGGER.debug(
                                    "Skipping departure due to direction mismatch. Required: '%s', actual: '%s'",
                                    self.direction,
                                    departure_direction,
                                )
                                continue

                        json_size = len(json.dumps(filtered_departures))
                        if json_size > MAX_SIZE_BYTES:
                            _LOGGER.info(
                                "Filtered departures JSON size exceeds limit: %d bytes for entry: %s . Ignoring some future departures to keep the size lower.",
                                json_size,
                                self.station,
                            )
                            break

                        if not self.keep_endstation:
                            if departure.get("destination") == self.station:
                                _LOGGER.debug(
                                    "Skipping departure as %s is the final stop.",
                                    self.station,
                                )
                                continue

                        if self.exclude_cancelled:
                            if departure.get("cancelled", False):
                                _LOGGER.debug(
                                    "Skipping cancelled departure: %s",
                                    departure,
                                )
                                continue

                        # Get train classes from the departure data.
                        train_classes = (
                            departure.get("trainClasses")
                            or departure.get("train_type")
                            or departure.get("type", [])
                        )

                        if isinstance(train_classes, str):
                            train_classes = [train_classes]

                        # If the API returns an empty list, we treat it as an "unknown" type,
                        # represented by an empty string, so it can be filtered.
                        if not train_classes and isinstance(train_classes, list):
                            api_classes_to_process = [""]
                        else:
                            api_classes_to_process = train_classes

                        # Normalize the train classes from the API using the mapping.
                        mapped_api_classes = {
                            TRAIN_TYPE_MAPPING.get(tc, tc)
                            for tc in api_classes_to_process
                        }

                        # Update the departure data with the normalized, more descriptive train classes.
                        departure["trainClasses"] = list(mapped_api_classes)

                        # Filter if any of the departure's train classes are in the ignored list.
                        if (
                            mapped_ignored_train_types
                            and not mapped_api_classes.isdisjoint(
                                mapped_ignored_train_types
                            )
                        ):
                            _LOGGER.debug(
                                "Ignoring departure due to train class. Mapped classes: %s",
                                mapped_api_classes,
                            )
                            continue

                        departure_time = departure["departure_datetime"]

                        delay_departure = (
                            departure.get("delayDeparture")
                            or departure.get("dep_delay")
                            or departure.get("delay")
                        )
                        if delay_departure is None:
                            delay_departure = 0
                        else:
                            delay_departure = int(delay_departure)

                        departure_time_adjusted = None
                        if departure_time and delay_departure is not None:
                            departure_time_adjusted = departure_time + timedelta(
                                minutes=delay_departure
                            )
                            # Keep existing human-readable time string
                            departure["departure_current"] = (
                                departure_time_adjusted.strftime("%Y-%m-%dT%H:%M")
                                if departure_time_adjusted.date() != today
                                else departure_time_adjusted.strftime("%H:%M")
                            )
                            # Add new machine-readable Unix timestamp
                            departure["departure_timestamp"] = int(
                                departure_time_adjusted.timestamp()
                            )

                        if self.show_occupancy:
                            occupancy = departure.get("occupancy")
                            if occupancy:
                                departure["occupancy"] = occupancy

                        # Platform change detection
                        platform = departure.get("platform")
                        scheduled_platform = departure.get("scheduledPlatform")
                        if (
                            platform
                            and scheduled_platform
                            and platform != scheduled_platform
                        ):
                            departure["changed_platform"] = True
                        else:
                            departure["changed_platform"] = False

                        # Wagon Order (Pass-through + Sector Extraction)
                        if "wagonorder" in departure:
                            departure["wagon_order"] = departure["wagonorder"]

                        # Extract sectors from platform string (e.g. "5 D-G")
                        if platform and isinstance(platform, str):
                            # Matches " D-G", " A", " A-C", with leading space or start
                            sector_match = re.search(r"\s([A-G](-[A-G])?)$", platform)
                            if sector_match:
                                departure["platform_sectors"] = sector_match.group(1)

                        # QoS (Pass-through + Message Parsing)
                        if "qos" in departure:
                            departure["qos"] = departure["qos"]

                        # Parse facilities from messages
                        facilities = {}
                        msg_texts = []
                        if "messages" in departure and isinstance(
                            departure["messages"], dict
                        ):
                            for msg_list in departure["messages"].values():
                                if isinstance(msg_list, list):
                                    for msg in msg_list:
                                        if isinstance(msg, dict):
                                            msg_texts.append(msg.get("text", ""))

                        for text in msg_texts:
                            lower_text = text.lower()
                            if "wlan" in lower_text or "wifi" in lower_text:
                                if (
                                    "nicht" in lower_text
                                    or "gestört" in lower_text
                                    or "ausfall" in lower_text
                                    or "defekt" in lower_text
                                ):
                                    facilities["wifi"] = False
                            if (
                                "bistro" in lower_text
                                or "restaurant" in lower_text
                                or "catering" in lower_text
                            ):
                                if (
                                    "nicht" in lower_text
                                    or "gestört" in lower_text
                                    or "geschlossen" in lower_text
                                ):
                                    facilities["bistro"] = False

                        if facilities:
                            departure["facilities"] = facilities

                        # Real-time Route Progress
                        route_details = []
                        if "route" in departure and isinstance(
                            departure["route"], list
                        ):
                            for stop in departure["route"]:
                                if isinstance(stop, dict):
                                    stop_name = stop.get("name")
                                    if stop_name:
                                        details = {"name": stop_name}
                                        # Add delay info if available
                                        if "arr_delay" in stop:
                                            details["arr_delay"] = stop["arr_delay"]
                                        if "dep_delay" in stop:
                                            details["dep_delay"] = stop["dep_delay"]
                                        route_details.append(details)
                                elif isinstance(stop, str):
                                    # Handle simple string list
                                    route_details.append({"name": stop})

                        if route_details:
                            departure["route_details"] = route_details

                        # Trip-ID
                        departure["trip_id"] = departure.get(
                            "trainId"
                        ) or departure.get("tripId")

                        scheduled_arrival = departure.get("scheduledArrival")
                        delay_arrival = departure.get("delayArrival")
                        if delay_arrival is None:
                            delay_arrival = 0

                        arrival_time_adjusted = None
                        if scheduled_arrival is not None:
                            try:
                                arrival_time = None
                                if isinstance(scheduled_arrival, (int, float)):
                                    arrival_time = dt_util.utc_from_timestamp(
                                        int(scheduled_arrival)
                                    ).astimezone(now.tzinfo)
                                elif isinstance(scheduled_arrival, str):
                                    # Attempt robust parsing using HA helper
                                    parsed_dt = dt_util.parse_datetime(
                                        scheduled_arrival
                                    )
                                    if parsed_dt:
                                        if parsed_dt.tzinfo is None:
                                            arrival_time = now.replace(
                                                year=parsed_dt.year,
                                                month=parsed_dt.month,
                                                day=parsed_dt.day,
                                                hour=parsed_dt.hour,
                                                minute=parsed_dt.minute,
                                                second=parsed_dt.second,
                                                microsecond=parsed_dt.microsecond,
                                            )
                                            # Use a 5-minute grace window to handle next-day rollover
                                            if arrival_time < now - timedelta(
                                                minutes=5
                                            ):
                                                arrival_time += timedelta(days=1)
                                        else:
                                            arrival_time = parsed_dt.astimezone(
                                                now.tzinfo
                                            )
                                    else:
                                        # Fallback for HH:MM format (assume today)
                                        try:
                                            temp_dt = datetime.strptime(
                                                scheduled_arrival, "%H:%M"
                                            )
                                            arrival_time = now.replace(
                                                hour=temp_dt.hour,
                                                minute=temp_dt.minute,
                                                second=0,
                                                microsecond=0,
                                            )
                                            # Use a 5-minute grace window to handle next-day rollover
                                            if arrival_time < now - timedelta(
                                                minutes=5
                                            ):
                                                arrival_time += timedelta(days=1)
                                        except (ValueError, TypeError):
                                            _LOGGER.error(
                                                "Invalid time format for scheduledArrival fallback: %s",
                                                scheduled_arrival,
                                            )
                                else:
                                    _LOGGER.warning(
                                        f"Unsupported scheduledArrival type: {type(scheduled_arrival)}"
                                    )

                                if arrival_time:
                                    arrival_delay = int(delay_arrival)
                                    arrival_time_adjusted = arrival_time + timedelta(
                                        minutes=arrival_delay
                                    )
                                    # Keep existing human-readable time string
                                    departure["arrival_current"] = (
                                        arrival_time_adjusted.strftime("%Y-%m-%dT%H:%M")
                                        if arrival_time_adjusted.date() != today
                                        else arrival_time_adjusted.strftime("%H:%M")
                                    )
                                    # Add new machine-readable Unix timestamp
                                    departure["arrival_timestamp"] = int(
                                        arrival_time_adjusted.timestamp()
                                    )

                            except (TypeError, ValueError):
                                _LOGGER.error(
                                    "Invalid time format for scheduledArrival: %s",
                                    scheduled_arrival,
                                )

                        # Fallback for arrival time if not present
                        if "arrival_current" not in departure and departure.get(
                            "departure_current"
                        ):
                            departure["arrival_current"] = departure.get(
                                "departure_current"
                            )
                        # Fallback for the new timestamp attribute
                        if "arrival_timestamp" not in departure and departure.get(
                            "departure_timestamp"
                        ):
                            departure["arrival_timestamp"] = departure.get(
                                "departure_timestamp"
                            )

                        effective_departure_time = departure_time
                        if not self.drop_late_trains:
                            effective_departure_time += timedelta(
                                minutes=delay_departure or 0
                            )

                        # Remove route attributes to lower sensor size limit
                        if not self.detailed:
                            for key in [
                                "id",
                                "stop_id_num",
                                "stateless",
                                "key",
                                "messages",
                                "mot",
                            ]:
                                departure.pop(key, None)
                            allowed_null_keys = {
                                "scheduledDeparture",
                                "scheduledTime",
                                "delay",
                                "delayDeparture",
                                "scheduledArrival",
                                "arrival_current",
                                "departure_current",
                                "sched_dep",
                                "sched_arr",
                                "dep",
                                "datetime",
                            }
                            keys_to_remove = [
                                k
                                for k, v in departure.items()
                                if (v is None or (isinstance(v, str) and not v.strip()))
                                and k not in allowed_null_keys
                            ]
                            for key in keys_to_remove:
                                departure.pop(key)

                        if not self.keep_route:
                            for key in ["route", "via", "prev_route", "next_route"]:
                                departure.pop(key, None)

                        # Remove temporary datetime object
                        departure.pop("departure_datetime", None)

                        departure_seconds = (
                            effective_departure_time - now
                        ).total_seconds()
                        if departure_seconds >= self.offset:
                            filtered_departures.append(departure)

                    _LOGGER.debug(
                        "Number of departures added to the filtered list: %d",
                        len(filtered_departures),
                    )
                    if filtered_departures:
                        self._last_valid_value = filtered_departures[
                            : self.next_departures
                        ]
                        _LOGGER.debug(
                            "Fetched and cached %d valid departures",
                            len(filtered_departures),
                        )
                        return filtered_departures[: self.next_departures]
                    else:
                        _LOGGER.warning(
                            "Departures fetched but all were filtered out. Using cached data."
                        )
                        return self._last_valid_value or []
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout fetching data from %s", self.api_url)
                return self._last_valid_value or []
            except aiohttp.ClientError as e:
                _LOGGER.error("Client error fetching data from %s: %s", self.api_url, e)
                return self._last_valid_value or []
            except json.JSONDecodeError as e:
                _LOGGER.error("JSON decode error from %s: %s", self.api_url, e)
                return self._last_valid_value or []
            except Exception as e:
                _LOGGER.error("Unexpected error fetching data: %s", e)
                return self._last_valid_value or []

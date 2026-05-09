"""
Home Assistant integration for Deutsche Bahn (DB) information screens.

This module provides the core logic and coordinator for fetching train departure
information from the Deutsche Bahn (DBF) API and regional providers.
"""

from typing import Any
import async_timeout
import asyncio
import copy
import logging
import json
import re
import voluptuous as vol
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode, urlparse

from homeassistant import config_entries
from homeassistant.components import repairs as ha_repairs
from . import repairs
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.network import get_url
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_PAUSED,
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
    CONF_DEDUPLICATE_KEY,
    DEFAULT_DEDUPLICATE_KEY,
    CONF_VIA_STATIONS_LOGIC,
    TRAIN_TYPE_MAPPING,
    CONF_EXCLUDE_CANCELLED,
    CONF_SHOW_OCCUPANCY,
    CONF_FAVORITE_TRAINS,
    CONF_SERVER_TYPE,
    CONF_SERVER_URL,
    SERVER_TYPE_CUSTOM,
    SERVER_TYPE_OFFICIAL,
    SERVER_TYPE_FASERF,
    SERVER_URL_OFFICIAL,
    SERVER_URL_FASERF,
    normalize_data_source,
    DATA_SOURCE_MAP,
)
from .utils import parse_datetime_flexible, prune_response_cache, simple_serializer

_LOGGER = logging.getLogger(__name__)

# Key: URL, Value: (Timestamp, Data)
RESPONSE_CACHE: dict[str, Any] = {}
CACHE_TTL = timedelta(seconds=55)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """
    Set up DB Infoscreen from a config entry.

    Initializes the data coordinator, registers services (watch_train, track_connection),
    and sets up the platforms (sensor, calendar, binary_sensor).
    """
    hass.data.setdefault(DOMAIN, {})

    # Set up the coordinator
    coordinator = DBInfoScreenCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # Set up all platforms: sensor, calendar, binary_sensor
    await hass.config_entries.async_forward_entry_setups(
        config_entry, ["sensor", "calendar", "binary_sensor"]
    )

    # Add an update listener for options
    config_entry.add_update_listener(update_listener)

    if not hass.services.has_service(DOMAIN, "watch_train"):

        async def async_watch_train(service_call):
            """Handle the watch_train service call."""
            train_id = service_call.data["train_id"]
            notify_service = service_call.data["notify_service"]

            # Broadcast to all coordinators
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, DBInfoScreenCoordinator):
                    coord.watched_trips[train_id] = {
                        "notify_service": notify_service,
                        "delay_threshold": service_call.data.get("delay_threshold", 5),
                        "notify_on_platform_change": service_call.data.get(
                            "notify_on_platform_change", True
                        ),
                        "notify_on_cancellation": service_call.data.get(
                            "notify_on_cancellation", True
                        ),
                        "last_notified_delay": -1,
                        "last_notified_platform": None,
                        "last_notified_cancellation": False,
                    }
            _LOGGER.debug("Trip %s added to all Watchlists", train_id)

        hass.services.async_register(
            DOMAIN,
            "watch_train",
            async_watch_train,
            schema=vol.Schema(
                {
                    vol.Required("train_id"): cv.string,
                    vol.Required("notify_service"): cv.string,
                    vol.Optional("delay_threshold", default=5): cv.positive_int,
                    vol.Optional("notify_on_platform_change", default=True): cv.boolean,
                    vol.Optional("notify_on_cancellation", default=True): cv.boolean,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "track_connection"):

        async def async_track_connection(service_call):
            """Handle the track_connection service call."""
            my_train_id = service_call.data["my_train_id"]
            change_station = service_call.data["change_station"]
            next_train_id = service_call.data["next_train_id"]

            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, DBInfoScreenCoordinator):
                    coord.tracked_connections[my_train_id] = {
                        "change_station": change_station,
                        "next_train_id": next_train_id,
                    }
            _LOGGER.debug(
                "Connection %s -> %s tracked in all coordinators",
                my_train_id,
                next_train_id,
            )

        hass.services.async_register(
            DOMAIN,
            "track_connection",
            async_track_connection,
            schema=vol.Schema(
                {
                    vol.Required("my_train_id"): cv.string,
                    vol.Required("change_station"): cv.string,
                    vol.Required("next_train_id"): cv.string,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "refresh_departures"):

        async def async_refresh_departures(service_call):
            """Handle the refresh_departures service call."""
            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, DBInfoScreenCoordinator):
                    await coord.async_refresh()
            _LOGGER.debug("Manual refresh triggered for all coordinators")

        hass.services.async_register(
            DOMAIN,
            "refresh_departures",
            async_refresh_departures,
        )

    if not hass.services.has_service(DOMAIN, "set_offset"):

        async def async_set_offset(service_call):
            """Handle the set_offset service call to dynamically adjust time offset."""
            target_station = service_call.data.get("station")
            new_offset = service_call.data.get("offset", "00:00")

            for coord in hass.data[DOMAIN].values():
                if isinstance(coord, DBInfoScreenCoordinator):
                    if (
                        target_station
                        and str(coord.station).lower() != str(target_station).lower()
                    ):
                        continue

                    new_seconds = coord.convert_offset_to_seconds(new_offset)
                    coord.offset = new_seconds
                    _LOGGER.info(
                        "Updating offset for station %s to %s (%d seconds)",
                        coord.station,
                        new_offset,
                        new_seconds,
                    )
                    await coord.async_refresh()

        hass.services.async_register(
            DOMAIN,
            "set_offset",
            async_set_offset,
            schema=vol.Schema(
                {
                    vol.Optional("station"): cv.string,
                    vol.Required("offset"): cv.string,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, "set_paused"):

        async def async_set_paused(service_call):
            """Handle the set_paused service call to toggle periodic updates."""
            target_station = service_call.data.get("station")
            paused = service_call.data["paused"]

            for entry in hass.config_entries.async_entries(DOMAIN):
                coordinator = hass.data[DOMAIN].get(entry.entry_id)
                if not coordinator:
                    continue

                if (
                    target_station
                    and str(coordinator.station).lower() != str(target_station).lower()
                ):
                    continue

                # Merge new paused state into existing options
                new_options = {**entry.options, CONF_PAUSED: paused}
                hass.config_entries.async_update_entry(entry, options=new_options)
                _LOGGER.info(
                    "Setting paused state for station %s to %s",
                    coordinator.station,
                    paused,
                )

        hass.services.async_register(
            DOMAIN,
            "set_paused",
            async_set_paused,
            schema=vol.Schema(
                {
                    vol.Optional("station"): cv.string,
                    vol.Required("paused"): cv.boolean,
                }
            ),
        )

    return True


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Migrate old entry from version 1 to 2."""
    _LOGGER.info("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}

        def migrate_dict(d: dict[str, Any]) -> None:
            if CONF_SERVER_URL not in d:
                # Use custom_api_url if it exists, otherwise use official
                url = d.get("custom_api_url")
                if not url:
                    url = SERVER_URL_OFFICIAL

                # Check if it looks like faserf or official
                if url == SERVER_URL_OFFICIAL:
                    d[CONF_SERVER_TYPE] = SERVER_TYPE_OFFICIAL
                elif url == SERVER_URL_FASERF:
                    d[CONF_SERVER_TYPE] = SERVER_TYPE_FASERF
                else:
                    d[CONF_SERVER_TYPE] = SERVER_TYPE_CUSTOM

                d[CONF_SERVER_URL] = url

            # Clean up old key
            if "custom_api_url" in d:
                del d["custom_api_url"]

        migrate_dict(new_data)
        migrate_dict(new_options)

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options, version=2
        )

    _LOGGER.info("Migration to version %s successful", config_entry.version)
    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """
    Unload a config entry.

    Unloads all platforms and removes the coordinator from hass.data.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, ["sensor", "calendar", "binary_sensor"]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def update_listener(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class DBInfoScreenCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """
    Data update coordinator for DB Infoscreen.

    Fetches data from the DBF/Regional API, processes train departures,
    handles filtering (via stations, directions, train types), and
    manages background tasks like train watching and connection tracking.
    """

    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
        """Initialize coordinator state from a config entry."""
        self.config_entry = config_entry

        # Get config from data and options
        config = {**config_entry.data, **config_entry.options}

        self.station = config[CONF_STATION]
        self.next_departures = int(
            config.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)
        )
        self.favorite_trains: list[str] = []
        fav_raw = config.get(CONF_FAVORITE_TRAINS, "")
        if isinstance(fav_raw, str) and fav_raw.strip():
            self.favorite_trains = [
                s.strip() for s in re.split(r",|\|", fav_raw) if s.strip()
            ]

        self.watched_trips: dict[str, dict[str, Any]] = {}
        self.tracked_connections: dict[str, dict[str, Any]] = {}
        self.departure_history: dict[str, Any] = {}
        self.hide_low_delay: bool = bool(config.get(CONF_HIDE_LOW_DELAY, False))
        self.detailed: bool = bool(config.get(CONF_DETAILED, False))
        self.past_60_minutes: bool = bool(config.get(CONF_PAST_60_MINUTES, False))
        self.data_source = normalize_data_source(
            config.get(CONF_DATA_SOURCE, "IRIS-TTS")
        )
        self.offset = self.convert_offset_to_seconds(
            str(config.get(CONF_OFFSET, DEFAULT_OFFSET))
        )
        self.via_stations = config.get(CONF_VIA_STATIONS, [])
        self.direction = config.get(CONF_DIRECTION, "")
        self.excluded_directions = config.get(CONF_EXCLUDED_DIRECTIONS, "")

        ignored_raw = config.get(CONF_IGNORED_TRAINTYPES, "")
        if isinstance(ignored_raw, list):
            self.ignored_train_types = ignored_raw
        else:
            self.ignored_train_types = [
                t.strip() for t in str(ignored_raw).split(",") if t.strip()
            ]

        self.drop_late_trains = config.get(CONF_DROP_LATE_TRAINS, False)
        self.keep_route = config.get(CONF_KEEP_ROUTE, False)
        self.keep_endstation = config.get(CONF_KEEP_ENDSTATION, False)
        self.deduplicate_departures = config.get(CONF_DEDUPLICATE_DEPARTURES, False)
        self.deduplicate_key = config.get(CONF_DEDUPLICATE_KEY, DEFAULT_DEDUPLICATE_KEY)
        self.exclude_cancelled = config.get(CONF_EXCLUDE_CANCELLED, False)
        self.show_occupancy = config.get(CONF_SHOW_OCCUPANCY, False)
        self.platforms = config.get(CONF_PLATFORMS, "")
        self.paused = bool(config.get(CONF_PAUSED, False))
        self.via_stations_logic = config.get(CONF_VIA_STATIONS_LOGIC, "OR")
        admode = config.get(CONF_ADMODE, "")
        raw_update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        update_interval = int(max(raw_update_interval, MIN_UPDATE_INTERVAL))
        self._api_update_interval = update_interval * 60
        self._last_api_fetch = 0.0
        self._raw_api_data = None

        # Fixed local update interval for calculation/pruning (30 seconds)
        # If interval is 0, we disable automatic updates
        local_calc_interval = timedelta(seconds=30) if update_interval > 0 else None

        station_cleaned = " ".join(str(self.station).split())
        encoded_station = quote(station_cleaned, safe="-:,")
        self._last_valid_value: list[dict[str, Any]] = []
        # Use the server URL from the config entry, fall back to official if missing
        self._base_url = config.get(CONF_SERVER_URL, SERVER_URL_OFFICIAL)
        url = f"{self._base_url}/{encoded_station}.json"

        data_source_map = DATA_SOURCE_MAP

        # Assemble Fetch URL (Generic for caching)
        fetch_params = {}
        if admode == "arrival":
            fetch_params["admode"] = "arr"
        elif admode == "departure":
            fetch_params["admode"] = "dep"

        # Check if the data source is in the HAFAS list
        if self.data_source == "hafas=1":
            fetch_params["hafas"] = "1"
        elif self.data_source in data_source_map:
            key, value = data_source_map[self.data_source].split("=")
            fetch_params[key] = value

        if self.detailed:
            fetch_params["detailed"] = "1"
            fetch_params["wagonorder"] = "1"
        if self.past_60_minutes:
            fetch_params["past"] = "1"

        if self.platforms:
            fetch_params["platforms"] = self.platforms
        if len(self.via_stations) == 1:
            fetch_params["via"] = self.via_stations[0].strip()

        fetch_query = urlencode(fetch_params, quote_via=quote)
        self.fetch_url = f"{url}?{fetch_query}" if fetch_query else url

        # Assemble User API URL (Specific for metadata/web links)
        user_params = fetch_params.copy()
        if self.hide_low_delay:
            user_params["hidelowdelay"] = "1"

        user_query = urlencode(user_params, quote_via=quote)
        self.api_url = f"{url}?{user_query}" if user_query else url

        # Determine filtering strategy and logic
        self.via_stations_logic = str(config.get(CONF_VIA_STATIONS_LOGIC, "OR")).upper()

        # Track if any filtering was already done by the server for backward compatibility
        self._via_filtered_server_side = "via" in fetch_params
        self._platforms_filtered_server_side = "platforms" in fetch_params

        super().__init__(
            hass,
            _LOGGER,
            name=f"DB-Infoscreen {self.station}",
            update_interval=local_calc_interval,
        )
        self.config_entry = config_entry
        self._consecutive_errors = 0
        self._last_successful_update: datetime | None = None
        self._stale_issue_raised = False
        self.server_version: str | None = None
        _LOGGER.debug(
            "Coordinator initialized for station %s with update interval %d minutes",
            self.station,
            update_interval,
        )

    @property
    def web_url(self) -> str | None:
        """Return the human-readable DBF website URL (without .json)."""
        if hasattr(self, "api_url") and self.api_url:
            # Remove .json from the URL to get the web page
            url = self.api_url.replace(".json", "")
            # If the URL points to localhost/127.0.0.1, try to resolve to HA local IP
            # so that it works when accessed from outside (e.g. mobile app)
            if "127.0.0.1" in url or "localhost" in url:
                try:
                    # Try to get internal URL (e.g. http://192.168.1.10:8123)
                    internal_url = get_url(
                        self.hass, allow_internal=True, allow_external=False
                    )
                    if internal_url:
                        local_ip = urlparse(internal_url).hostname
                        if local_ip:
                            url = url.replace("127.0.0.1", local_ip).replace(
                                "localhost", local_ip
                            )
                except Exception as e:
                    _LOGGER.debug("Could not resolve local IP for web_url: %s", e)
            return url
        return None

    async def async_fetch_server_version(self):
        """Fetch server version from the API."""
        session = async_get_clientsession(self.hass)
        try:
            # Try the suggested workaround endpoint
            about_url = f"{self._base_url}/_about.json"
            async with async_timeout.timeout(10):
                async with session.get(about_url, allow_redirects=True) as response:
                    if response.status < 500:
                        data = await response.json()
                        if isinstance(data, dict):
                            # Search for version strings in the response
                            v = data.get("version")
                            av = data.get("api_version")
                            if v and v != "???":
                                self.server_version = str(v)
                            elif av:
                                self.server_version = f"API v{av}"
        except Exception as e:
            _LOGGER.debug(
                "Could not fetch server version from %s: %s", self._base_url, e
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

    def _process_wagon_order(self, wagon_order_data: list) -> dict | None:
        """
        Process the wagon order list and return a structured dictionary.
        Returns:
            {
                "text": "1. Klasse: A-B | Bordbistro: C",
                "structured": {
                    "first_class": ["A", "B"],
                    "second_class": ["C", "D"],
                    "bistro": ["E"]
                }
            }
        """
        if not wagon_order_data:
            return None

        sectors_first_class = set()
        sectors_second_class = set()
        sectors_bistro = set()

        for wagon in wagon_order_data:
            sections = wagon.get("sections", [])
            if not sections:
                continue

            wagon_type = wagon.get("type", "")
            wagon_class = str(wagon.get("class", ""))

            # 1. Class
            if wagon_class == "1" or wagon_class == "12":
                sectors_first_class.update(sections)

            # 2. Class
            if wagon_class == "2" or wagon_class == "12":
                sectors_second_class.update(sections)

            # Bistro/Restaurant
            if "WR" in wagon_type or "AR" in wagon_type or "Bistro" in wagon_type:
                sectors_bistro.update(sections)

        def format_sectors(sectors: set) -> str:
            sorted_sectors = sorted(list(sectors))
            if not sorted_sectors:
                return ""
            if len(sorted_sectors) > 1:
                return ", ".join(sorted_sectors)
            return sorted_sectors[0]

        parts = []
        s1 = format_sectors(sectors_first_class)
        if s1:
            parts.append(f"<b>1. Klasse:</b> {s1}")

        s2 = format_sectors(sectors_second_class)
        if s2:
            parts.append(f"<b>2. Klasse:</b> {s2}")

        sb = format_sectors(sectors_bistro)
        if sb:
            parts.append(f"<b>Bordbistro:</b> {sb}")

        if not parts:
            return None

        return {
            "text": " | ".join(parts),
            "structured": {
                "first_class": sorted(list(sectors_first_class)),
                "second_class": sorted(list(sectors_second_class)),
                "bistro": sorted(list(sectors_bistro)),
            },
        }

    async def _async_update_data(self):
        """Retrieve and process next departures for the configured station."""
        if self.paused:
            _LOGGER.debug("Updates are paused for %s", self.station)
            return self._last_valid_value or []
        now = dt_util.now()

        # Periodic cleanup of global cache
        prune_response_cache(RESPONSE_CACHE, CACHE_TTL)

        # Fetch server version if we don't have it yet
        if self.server_version is None:
            await self.async_fetch_server_version()

        do_api_fetch = False
        if (
            self._raw_api_data is None
            or now.timestamp() - self._last_api_fetch >= self._api_update_interval
        ):
            do_api_fetch = True

        if not do_api_fetch:
            _LOGGER.debug(
                "Skipping API fetch for %s, using local data (Next fetch in %d seconds)",
                self.station,
                int(
                    self._api_update_interval - (now.timestamp() - self._last_api_fetch)
                ),
            )
            data = self._raw_api_data
        elif self.fetch_url in RESPONSE_CACHE:
            timestamp, cached_data = RESPONSE_CACHE[self.fetch_url]
            if now - timestamp < CACHE_TTL:
                _LOGGER.debug("Using globally cached response for %s", self.fetch_url)
                data = copy.deepcopy(cached_data)
                self._raw_api_data = data
                self._last_api_fetch = now.timestamp()
            else:
                _LOGGER.debug("Global cache expired for %s", self.fetch_url)
                RESPONSE_CACHE.pop(self.fetch_url, None)
                data = None
        else:
            data = None

        if data is None:
            import aiohttp

            session = async_get_clientsession(self.hass)
            max_retries = 2
            retry_delay = 1

            for attempt in range(max_retries + 1):
                try:
                    async with session.get(
                        self.fetch_url, timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 429:
                            _LOGGER.warning(
                                "Rate limit hit for %s (429 Too Many Requests). Skipping retries for this cycle.",
                                self.fetch_url,
                            )
                            return self._last_valid_value or []

                        data = await response.json()
                        if asyncio.iscoroutine(data) or (
                            hasattr(data, "__await__")
                            and not isinstance(data, (dict, list))
                        ):
                            data = await data

                        RESPONSE_CACHE[self.fetch_url] = (now, copy.deepcopy(data))
                        self._raw_api_data = data
                        self._last_api_fetch = now.timestamp()
                        break  # Success, exit retry loop
                except aiohttp.ClientResponseError as err:
                    if err.status == 429:
                        _LOGGER.warning(
                            "Rate limit hit for %s (429 Too Many Requests). skipping retries.",
                            self.fetch_url,
                        )
                        return self._last_valid_value or []
                    if attempt < max_retries:
                        _LOGGER.warning(
                            "Attempt %d failed fetching data from %s: %s. Retrying in %d seconds...",
                            attempt + 1,
                            self.fetch_url,
                            err,
                            retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        _LOGGER.error(
                            "Failed to fetch data from %s after %d retries: %s",
                            self.fetch_url,
                            max_retries,
                            err,
                        )
                        # Activate Repairs issue
                        self._handle_update_error(str(err))
                        return self._last_valid_value or []
                except (
                    asyncio.TimeoutError,
                    aiohttp.ClientError,
                    ValueError,
                    Exception,
                ) as err:
                    if attempt < max_retries:
                        _LOGGER.warning(
                            "Attempt %d failed fetching data from %s: %s. Retrying in %d seconds...",
                            attempt + 1,
                            self.fetch_url,
                            err,
                            retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        _LOGGER.error(
                            "Failed to fetch data from %s after %d retries: %s",
                            self.fetch_url,
                            max_retries,
                            err,
                        )
                        # Activate Repairs issue
                        self._handle_update_error(str(err))
                        return self._last_valid_value or []

        if not isinstance(data, dict):
            _LOGGER.error("Expected dict from API, got %s", type(data))
            return self._last_valid_value or []

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

        # Success! Clear any error tracking and repair issues
        self._consecutive_errors = 0
        self._last_successful_update = now
        self._stale_issue_raised = False
        # --- PRE-PROCESSING: Parse time for all departures ---
        departures_with_time = []
        # Use a deep copy to avoid modifying the cached/mock objects in-place
        for departure in copy.deepcopy(raw_departures):
            if not departure:
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

            # Use centralized robust parsing
            departure_time_obj = parse_datetime_flexible(departure_time_str, now)

            if not departure_time_obj:
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
                    and self.excluded_directions.lower() in departure_direction.lower()
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
                "Deduplication is enabled. Processing %d departures.",
                len(departures_with_time),
            )
            # Sort by time to ensure we process trips in chronological order
            departures_to_process.sort(key=lambda d: d["departure_datetime"])

            final_departures = []
            # Keep track of the last processed departure for each unique key to handle multiple trips per line
            last_kept_for_key: dict[Any, dict[str, Any]] = {}

            for departure in departures_to_process:
                # Resolve the unique trip identifier using the configured key template
                key_trip_id = ""
                raw_key_parts = re.findall(r"\{([^}]+)\}", self.deduplicate_key)
                if raw_key_parts:
                    for part in raw_key_parts:
                        val = departure.get(part)
                        if val is not None:
                            # Normalize string components (strip whitespace, lowercase) for robustness
                            if isinstance(val, str):
                                val = val.strip().lower()
                            key_trip_id += str(val)
                else:
                    # Fallback if no placeholders found (legacy behavior or static string)
                    key_trip_id = self.deduplicate_key.strip().lower()

                key_line = (
                    str(departure.get("line") or departure.get("train") or "")
                    .strip()
                    .lower()
                )
                key_dest = str(departure.get("destination") or "").strip().lower()

                # Build the unique key using trip_id if available, otherwise fallback to line+dest
                if key_trip_id:
                    unique_key: Any = key_trip_id
                elif key_line or key_dest:
                    unique_key = (key_line, key_dest)
                else:
                    # If we don't even have line/dest/trip_id, treat as unique to avoid over-deduplication
                    final_departures.append(departure)
                    continue

                if unique_key not in last_kept_for_key:
                    final_departures.append(departure)
                    last_kept_for_key[unique_key] = departure
                else:
                    # We have seen this trip before. Check the time difference with the LAST kept one.
                    existing_departure = last_kept_for_key[unique_key]
                    time_diff = abs(
                        (
                            departure["departure_datetime"]
                            - existing_departure["departure_datetime"]
                        ).total_seconds()
                    )

                    # If the new one is within 2 minutes of the previous one, it's considered a duplicate.
                    if time_diff <= 120:
                        _LOGGER.debug(
                            "Filtering out duplicate departure. Key: %s, Keeping (earlier): %s, Removing (later): %s",
                            unique_key,
                            existing_departure.get(
                                "id", existing_departure.get("line")
                            ),
                            departure.get("id", departure.get("line")),
                        )
                        continue
                    else:
                        # Time difference is large enough (> 2 mins). This is a NEW trip for the same key.
                        final_departures.append(departure)
                        last_kept_for_key[unique_key] = departure

            departures_to_process = final_departures
            _LOGGER.debug(
                "Deduplication complete. Remaining departures: %d",
                len(departures_to_process),
            )

        # --- MAIN FILTERING AND PROCESSING ---
        filtered_departures: list[dict[str, Any]] = []
        current_size = 2  # Estimate for empty list '[]'

        # Map the configured ignored train types to the normalized values for correct comparison.
        # e.g., if config is ['S'], this becomes {'S-Bahn'}.
        ignored_train_types = self.ignored_train_types
        mapped_ignored_train_types = {
            TRAIN_TYPE_MAPPING.get(t, t) for t in ignored_train_types
        }

        # Some data sources might use other values, ensure compatibility.
        if "S" in ignored_train_types:
            mapped_ignored_train_types.add("S-Bahn")
            mapped_ignored_train_types.add("s_bahn")
        if "StadtBus" in ignored_train_types:
            mapped_ignored_train_types.add("MetroBus")
            mapped_ignored_train_types.add("bus")
        if "F" in ignored_train_types:
            mapped_ignored_train_types.add("Fernverkehr")
            mapped_ignored_train_types.add("long_distance")
        if "N" in ignored_train_types:
            mapped_ignored_train_types.add("Regionalverkehr")
            mapped_ignored_train_types.add("regional_db")

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
                    or self.direction.lower() not in departure_direction.lower()
                ):
                    _LOGGER.debug(
                        "Skipping departure due to direction mismatch. Required: '%s', actual: '%s'",
                        self.direction,
                        departure_direction,
                    )
                    continue

            if not self.keep_endstation:
                dest = str(departure.get("destination", "")).strip().lower()
                stat = str(self.station).strip().lower()
                if dest == stat:
                    _LOGGER.debug(
                        "Skipping departure as %s is the final stop (normalized destination match).",
                        self.station,
                    )
                    continue

            is_cancelled = (
                departure.get("cancelled", False)
                or departure.get("isCancelled", False)
                or departure.get("is_cancelled", False)
            )
            departure["is_cancelled"] = is_cancelled  # Normalize

            if self.exclude_cancelled:
                if is_cancelled:
                    _LOGGER.debug(
                        "Skipping cancelled departure: %s",
                        departure,
                    )
                    continue

            # Platform filter (LOCAL)
            if self.platforms and not self._platforms_filtered_server_side:
                departure_platform = str(departure.get("platform") or "")
                # Allow multiple platforms separated by comma in config
                allowed_platforms = [
                    p.strip() for p in self.platforms.split(",") if p.strip()
                ]
                if allowed_platforms and departure_platform not in allowed_platforms:
                    _LOGGER.debug(
                        "Skipping departure due to platform mismatch. Allowed: %s, actual: '%s'",
                        allowed_platforms,
                        departure_platform,
                    )
                    continue

            # Via Stations filter (LOCAL)
            if self.via_stations and not self._via_filtered_server_side:
                # Check both "route" (list of dicts) and "via" (list of strings)
                route_raw = departure.get("route") or []
                via_raw = departure.get("via") or []

                # Consolidate all station names into a lowercase set for matching
                stations_on_route = set()

                # Process route list
                for stop in route_raw:
                    if isinstance(stop, dict):
                        stations_on_route.add(stop.get("name", "").lower())
                    else:
                        stations_on_route.add(str(stop).lower())

                # Process via list
                for stop in via_raw:
                    stations_on_route.add(str(stop).lower())

                # Also include destination in the check
                dest = departure.get("destination", "").lower()
                if dest:
                    stations_on_route.add(dest)

                via_matches = [
                    v.lower() in stations_on_route for v in self.via_stations
                ]

                if self.via_stations_logic == "AND":
                    matches = all(via_matches)
                else:
                    matches = any(via_matches)

                if not matches:
                    _LOGGER.debug(
                        "Skipping departure due to via station mismatch (%s). Required: %s, route: %s",
                        self.via_stations_logic,
                        self.via_stations,
                        list(stations_on_route),
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

            # If the API returns an empty list, we try to infer it from the train name.
            if not train_classes and isinstance(train_classes, list):
                train_name = str(departure.get("train", "")).upper()
                if "ICE" in train_name:
                    api_classes_to_process = ["ICE"]
                elif "IC" in train_name or "EC" in train_name or "TGV" in train_name:
                    api_classes_to_process = ["ICE"]
                elif "RE" in train_name:
                    api_classes_to_process = ["RE"]
                elif "RB" in train_name:
                    api_classes_to_process = ["RB"]
                elif "S " in train_name or "S1" in train_name or "S2" in train_name:
                    api_classes_to_process = ["S"]
                else:
                    api_classes_to_process = [""]
            else:
                api_classes_to_process = train_classes

            # Normalize the train classes from the API using the mapping.
            mapped_api_classes = {
                TRAIN_TYPE_MAPPING.get(tc, tc) for tc in api_classes_to_process
            }

            # Update the departure data with the normalized, more descriptive train classes.
            departure["trainClasses"] = list(mapped_api_classes)

            # Filter if any of the departure's train classes are in the ignored list.
            if mapped_ignored_train_types and not mapped_api_classes.isdisjoint(
                mapped_ignored_train_types
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
            try:
                if delay_departure is None or delay_departure == "":
                    delay_departure = 0
                else:
                    delay_departure = int(delay_departure)
            except ValueError:
                delay_departure = 0

            departure["delay"] = delay_departure  # Normalization

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
            else:
                # Explicitly remove occupancy if disabled
                departure.pop("occupancy", None)

            # Platform change detection
            platform = departure.get("platform")
            scheduled_platform = departure.get("scheduledPlatform")
            if platform and scheduled_platform and platform != scheduled_platform:
                departure["changed_platform"] = True
            else:
                departure["changed_platform"] = False

            # Wagon Order (Pass-through + Sector Extraction + HTML Generation)
            wagon_order_data = departure.get("wagonorder")
            if wagon_order_data:
                # If it's a list, it's the detailed structure
                if isinstance(wagon_order_data, list):
                    wagon_info = self._process_wagon_order(wagon_order_data)
                    if wagon_info:
                        departure["wagon_order_html"] = wagon_info.get("text")
                        departure["wagon_order_structured"] = wagon_info.get(
                            "structured"
                        )
                departure["wagon_order"] = wagon_order_data

            # Extract sectors from platform string (e.g. "5 D-G")
            if platform and isinstance(platform, str):
                # Matches " D-G", " A", " A-C", with leading space or start
                sector_match = re.search(r"\s([A-G](-[A-G])?)$", platform)
                if sector_match:
                    departure["platform_sectors"] = sector_match.group(1)

            # QoS (Pass-through + Message Parsing)
            if "qos" in departure:
                pass

            # Parse facilities from messages
            facilities = {}
            msg_texts = []
            if "messages" in departure and isinstance(departure["messages"], dict):
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
            if "route" in departure and isinstance(departure["route"], list):
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
            departure["trip_id"] = departure.get("trainId") or departure.get("tripId")

            scheduled_arrival = departure.get("scheduledArrival")
            delay_arrival = departure.get("delayArrival")
            try:
                if delay_arrival is None or delay_arrival == "":
                    delay_arrival = 0
                else:
                    delay_arrival = int(delay_arrival)
            except ValueError:
                delay_arrival = 0

            departure["delay_arrival"] = delay_arrival  # Normalization

            arrival_time_adjusted = None
            if scheduled_arrival is not None:
                # Use robust centralized parsing
                arrival_time = parse_datetime_flexible(scheduled_arrival, now)

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
                else:
                    _LOGGER.error(
                        "Invalid time format for scheduledArrival: %s",
                        scheduled_arrival,
                    )

            # Fallback for arrival time if not present
            if "arrival_current" not in departure and departure.get(
                "departure_current"
            ):
                departure["arrival_current"] = departure.get("departure_current")
            # Fallback for the new timestamp attribute
            if "arrival_timestamp" not in departure and departure.get(
                "departure_timestamp"
            ):
                departure["arrival_timestamp"] = departure.get("departure_timestamp")

            effective_departure_time = departure_time
            if not self.drop_late_trains:
                effective_departure_time += timedelta(minutes=delay_departure or 0)

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
                    "trip_id",  # Ensure trip_id is allowed to be None
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

            departure_seconds = (effective_departure_time - now).total_seconds()
            if departure_seconds >= self.offset:
                # Compute size with candidate included
                # We do this by serializing iteratively and checking size.
                try:
                    # Serialize just this item
                    item_json = json.dumps(departure, default=simple_serializer)
                    item_size = len(item_json)

                    # Calculate overhead: comma separator if list is not empty
                    overhead = 1 if filtered_departures else 0

                    potential_size = current_size + item_size + overhead

                    if potential_size > MAX_SIZE_BYTES:
                        _LOGGER.info(
                            "Filtered departures JSON size would exceed limit: %d bytes (limit %d) for entry: %s. Stopping here.",
                            potential_size,
                            MAX_SIZE_BYTES,
                            self.station,
                        )
                        break

                    filtered_departures.append(departure)
                    current_size += item_size + overhead

                except (TypeError, ValueError) as e:
                    _LOGGER.error("Failed to serialize departure for size check: %s", e)
                    continue

        _LOGGER.debug(
            "Number of departures added to the filtered list: %d",
            len(filtered_departures),
        )

        # Alternative Connections
        # For each departure, find other trains going to the same destination
        # that depart later. This helps users find backup options.
        if self.detailed and len(filtered_departures) > 1:
            for i, dep in enumerate(filtered_departures):
                dest_search: str | None = dep.get("destination")
                if not dest_search:
                    continue

                alternatives = []
                for j, other_dep in enumerate(filtered_departures):
                    if i == j:
                        continue
                    if other_dep.get("destination") == dest_search:
                        # Only include if it departs later
                        my_time = dep.get("departure_timestamp")
                        other_time = other_dep.get("departure_timestamp")
                        if my_time and other_time and other_time > my_time:
                            alternatives.append(
                                {
                                    "train": other_dep.get("train"),
                                    "scheduledDeparture": other_dep.get(
                                        "scheduledDeparture"
                                    ),
                                    "platform": other_dep.get("platform"),
                                }
                            )

                if alternatives:
                    dep["alternative_connections"] = list(alternatives)[
                        :3
                    ]  # Limit to 3

        # Punctuality Statistics
        # We track history for ALL departures that passed deduplication,
        # so the stats represent the station overall, not just the filtered subset.
        self._update_history(departures_to_process)

        # Favorite Trains Filtering
        if self.favorite_trains:
            fav_filtered = []
            for dep in filtered_departures:
                train_name = dep.get("train", "")
                if any(fav in train_name for fav in self.favorite_trains):
                    fav_filtered.append(dep)
            filtered_departures = fav_filtered
            _LOGGER.debug(
                "Filtered departures by favorite trains. Remaining: %d",
                len(filtered_departures),
            )

        if filtered_departures:
            # Cache the visible ones if available
            self._last_valid_value = list(filtered_departures)

            # Real-time Connection Tracking
            if self.tracked_connections:
                for dep in filtered_departures:
                    my_train_id = dep.get("train")
                    if not my_train_id:
                        continue

                    conn_config = self.tracked_connections.get(my_train_id)
                    if not conn_config:
                        trip_id = dep.get("trip_id")
                        if trip_id:
                            conn_config = self.tracked_connections.get(trip_id)

                    if conn_config:
                        change_station = conn_config["change_station"]
                        # If we have trip_id, we can potentially get full route.
                        # For now, let's just make the second API call.
                        next_train_id = conn_config["next_train_id"]
                        next_dep = await self._get_train_departure_at_station(
                            change_station, next_train_id
                        )

                        if next_dep:
                            dep["connection_info"] = {
                                "target_train": next_dep.get("train"),
                                "target_platform": next_dep.get("platform"),
                                "target_delay": next_dep.get("delayDeparture"),
                                "transfer_station": change_station,
                            }

            return list(filtered_departures)[: int(self.next_departures)]
        else:
            _LOGGER.warning(
                "Departures fetched but all were filtered out. Using cached data."
            )
            return self._last_valid_value or []

    async def _check_watched_trips(self, departures):
        """Check for important updates on watched trains and send notifications."""
        if not self.watched_trips:
            return

        to_remove = []

        for train_id_to_watch, watch_config in self.watched_trips.items():
            # Find the trip in current departures
            trip_found = None
            for dep in departures:
                if (
                    dep.get("train") == train_id_to_watch
                    or dep.get("trip_id") == train_id_to_watch
                ):
                    trip_found = dep
                    break

            if not trip_found:
                # Increment missed counter
                # watch_config should not be None here as it comes from keys()
                missed = int(watch_config.get("missed_update_count") or 0) + 1
                watch_config["missed_update_count"] = missed
                if missed >= 3:
                    to_remove.append(train_id_to_watch)
                continue

            # Found it, reset counter
            watch_config["missed_update_count"] = 0

            delay = (
                trip_found.get("delay")
                if "delay" in trip_found
                else trip_found.get("delayDeparture", 0)
            )
            platform = trip_found.get("platform")
            is_cancelled = (
                trip_found.get("is_cancelled")
                if "is_cancelled" in trip_found
                else (
                    trip_found.get("cancelled", False)
                    or trip_found.get("isCancelled", False)
                )
            )
            destination = trip_found.get("destination")

            notify = False
            message = f"Update for {trip_found.get('train')} to {destination}: "

            # 1. Check Delay
            try:
                if watch_config is not None:
                    delay_int = int(delay) if delay else 0
                    current_threshold = watch_config.get("delay_threshold")
                    threshold = int(
                        current_threshold if current_threshold is not None else 0
                    )
                    last_delay = watch_config.get("last_notified_delay")
                    if delay_int >= threshold and delay_int != last_delay:
                        notify = True
                        message += f"Delay is now {delay_int} min. "
                        watch_config["last_notified_delay"] = delay_int
            except (ValueError, TypeError):
                pass

            # 2. Check Platform
            if (
                watch_config["notify_on_platform_change"]
                and platform
                and platform != watch_config["last_notified_platform"]
            ):
                if watch_config["last_notified_platform"] is not None:
                    notify = True
                    message += f"Platform changed to {platform}. "
                watch_config["last_notified_platform"] = platform

            # 3. Check Cancellation
            if (
                watch_config["notify_on_cancellation"]
                and is_cancelled
                and not watch_config["last_notified_cancellation"]
            ):
                notify = True
                message += "Train is CANCELLED! "
                watch_config["last_notified_cancellation"] = True

            if notify:
                try:
                    if watch_config is None or not watch_config.get("notify_service"):
                        raise ValueError("No notify service configured")

                    if "." not in str(watch_config["notify_service"]):
                        raise ValueError("Invalid notify service format (missing '.')")

                    service_parts = str(watch_config["notify_service"]).split(".")
                    domain = service_parts[0]
                    service = ".".join(service_parts[1:])

                    if not domain or not service:
                        raise ValueError(
                            "Invalid notify service format (empty domain or service)"
                        )

                    await self.hass.services.async_call(
                        domain, service, {"message": message, "title": "🚆 DB Watcher"}
                    )
                    _LOGGER.info(
                        "Sent notification for trip %s: %s", train_id_to_watch, message
                    )
                except Exception as e:
                    _LOGGER.error(
                        "Failed to send notification for trip %s: %s",
                        train_id_to_watch,
                        e,
                    )

        for train_id in to_remove:
            _LOGGER.debug("Removing stale watch for %s", train_id)
            self.watched_trips.pop(train_id, None)

    async def _get_train_departure_at_station(self, station, train_id):
        """
        Fetch departure/arrival information for a specific train at a different station.

        Used for connection tracking to see if a connecting train at a transfer
        station is delayed or on time.
        """
        station_cleaned = " ".join(station.split())
        encoded_station = quote(station_cleaned, safe=",-")
        url = f"{self._base_url}/{encoded_station}.json"

        # Check cache
        if url in RESPONSE_CACHE:
            timestamp, cached_data = RESPONSE_CACHE[url]
            if dt_util.now() - timestamp < CACHE_TTL:
                _LOGGER.debug("Using cached response for cascaded fetch at %s", url)
                data = copy.deepcopy(cached_data)
            else:
                del RESPONSE_CACHE[url]
                data = None
        else:
            data = None

        try:
            if data is None:
                import aiohttp

                session = async_get_clientsession(self.hass)
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    # Handle both sync and async raise_for_status for better test compatibility
                    response.raise_for_status()

                    data = await response.json()
                    # Fallback for some mock environments where json() returns a coroutine
                    if asyncio.iscoroutine(data) or (
                        hasattr(data, "__await__")
                        and not isinstance(data, (dict, list))
                    ):
                        data = await data

                    # Store in cache - deepcopy to prevent mutation during processing
                    RESPONSE_CACHE[url] = (dt_util.now(), copy.deepcopy(data))

            if not isinstance(data, dict):
                _LOGGER.debug(
                    "Unexpected data type from cascaded fetch for %s: %s",
                    station,
                    type(data),
                )
                return None
            for dep in data.get("departures", []):
                if dep.get("train") == train_id or dep.get("trip_id") == train_id:
                    return dep
        except Exception as e:
            _LOGGER.debug("Failed to fetch cascaded data for %s: %s", station, e)
        return None

    def _update_history(self, departures):
        """
        Update the 24-hour departure history for punctuality statistics.

        Records the final seen status (delay, cancellation) for each train instance.
        Used to calculate percentage-based punctuality metrics in sensors.
        """
        now_utc = datetime.now(timezone.utc)
        threshold_24h = now_utc - timedelta(hours=24)

        # 1. Purge old history
        self.departure_history = {
            tid: data
            for tid, data in self.departure_history.items()
            if data["timestamp"] > threshold_24h
        }

        # 2. Record/Update current departures
        for dep in departures:
            # Fallback to 'line' for APIs like AVV buses
            train = dep.get("train") or dep.get("line")
            trip_id = dep.get("trip_id")

            # Use parsed datetime as stable fallback for entries filtered early
            timestamp = dep.get("departure_timestamp") or dep.get("arrival_timestamp")
            if timestamp is None:
                dt_obj = dep.get("departure_datetime")
                if dt_obj is not None:
                    try:
                        timestamp = int(dt_obj.timestamp())
                    except (AttributeError, OSError, OverflowError):
                        timestamp = None

            history_key = (
                trip_id if trip_id else (f"{train}_{timestamp}" if timestamp else None)
            )

            if not history_key or not train:
                _LOGGER.debug(
                    "_update_history: skipping entry with no stable key. train=%s, trip_id=%s, timestamp=%s",
                    train,
                    trip_id,
                    timestamp,
                )
                continue

            # Local normalization for entries skipped in main loop
            raw_delay = (
                dep.get("delay")
                or dep.get("delayDeparture")
                or dep.get("dep_delay")
                or 0
            )
            try:
                delay_val = int(raw_delay) if raw_delay not in (None, "") else 0
            except (ValueError, TypeError):
                delay_val = 0

            is_cancelled_val = bool(
                dep.get("is_cancelled")
                or dep.get("cancelled")
                or dep.get("isCancelled")
            )

            self.departure_history[history_key] = {
                "train": train,
                "timestamp": (
                    dt_util.utc_from_timestamp(timestamp)
                    if isinstance(timestamp, (int, float))
                    else now_utc
                ),
                "delay": delay_val,
                "delay_arrival": dep.get("delay_arrival", 0),
                "is_cancelled": is_cancelled_val,
            }

    def _handle_update_error(self, error_message: str) -> None:
        """Register a data fetch error and check for stale data issues."""
        if "429" in error_message or "Too Many Requests" in error_message:
            return

        self._consecutive_errors += 1
        now = dt_util.now()
        if self.config_entry is None:
            return
        entry_id = self.config_entry.entry_id

        # Check for stale data (24+ hours without successful update)
        if self._last_successful_update:
            hours_since_update = (
                now - self._last_successful_update
            ).total_seconds() / 3600
            if hours_since_update >= 24 and not self._stale_issue_raised:
                self._stale_issue_raised = True
                repairs.create_stale_data_issue(
                    self.hass,
                    entry_id,
                    self.station,
                    int(hours_since_update),
                )
                _LOGGER.warning(
                    "Station %s has not updated successfully for %d hours. Creating repair issue.",
                    self.station,
                    int(hours_since_update),
                )

        # After 3 consecutive errors, create an API error issue
        if self._consecutive_errors >= 3:
            # Check if this might be a permanent station issue
            if self._consecutive_errors >= 10:
                repairs.create_station_unsupported_issue(
                    self.hass,
                    entry_id,
                    self.station,
                    self.data_source,
                )
                _LOGGER.warning(
                    "Station %s has failed %d times. May no longer be supported.",
                    self.station,
                    self._consecutive_errors,
                )
            else:
                repairs.create_api_error_issue(
                    self.hass,
                    entry_id,
                    self.station,
                    error_message,
                )

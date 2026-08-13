"""Config flow for DB Infoscreen integration."""

import logging
import re
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_ADMODE,
    CONF_CACHE_TTL,
    CONF_CALENDAR_EVENT_DURATION,
    CONF_CALENDAR_ONLY_DELAYED,
    CONF_CALENDAR_ONLY_FAVORITES,
    CONF_DATA_SOURCE,
    CONF_DEDUPLICATE_DEPARTURES,
    CONF_DEDUPLICATE_KEY,
    CONF_DETAILED,
    CONF_DIRECTION,
    CONF_DROP_LATE_TRAINS,
    CONF_ENABLE_TEXT_VIEW,
    CONF_EXCLUDE_CANCELLED,
    CONF_EXCLUDED_DIRECTIONS,
    CONF_FAVORITE_TRAINS,
    CONF_HIDE_LOW_DELAY,
    CONF_IGNORED_TRAINTYPES,
    CONF_KEEP_ENDSTATION,
    CONF_KEEP_ROUTE,
    CONF_NEXT_DEPARTURES,
    CONF_OFFSET,
    CONF_PAST_60_MINUTES,
    CONF_PAUSED,
    CONF_PLATFORMS,
    CONF_SERVER_TYPE,
    CONF_SERVER_URL,
    CONF_SHOW_OCCUPANCY,
    CONF_STATION,
    CONF_TEXT_VIEW_TEMPLATE,
    CONF_UPDATE_INTERVAL,
    CONF_VIA_STATIONS,
    CONF_VIA_STATIONS_LOGIC,
    CONF_WALK_TIME,
    DATA_SOURCE_OPTIONS,
    DEFAULT_CACHE_TTL,
    DEFAULT_CALENDAR_EVENT_DURATION,
    DEFAULT_DEDUPLICATE_KEY,
    DEFAULT_NEXT_DEPARTURES,
    DEFAULT_OFFSET,
    DEFAULT_TEXT_VIEW_TEMPLATE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    IGNORED_TRAINTYPES_OPTIONS,
    MAX_SENSORS,
    SERVER_TYPE_CUSTOM,
    SERVER_TYPE_FASERF,
    SERVER_TYPE_OFFICIAL,
    SERVER_URL_FASERF,
    SERVER_URL_OFFICIAL,
    normalize_data_source,
)
from .utils import async_get_stations, find_station_matches, normalize_whitespace

_LOGGER = logging.getLogger(__name__)

ADDON_STABLE_SLUG = "7da084a7_dbf"
ADDON_DEV_SLUG = "local_dbf"
ADDON_NAME = "DBF (DB-Infoscreen)"
DEFAULT_PORT = 8092


def _generate_entry_title(data: dict) -> str:
    """Generate a title for the config entry based on current settings."""
    station = data.get(CONF_STATION, "Unknown Station")
    via = data.get(CONF_VIA_STATIONS, [])
    direction = data.get(CONF_DIRECTION, "")
    platforms = data.get(CONF_PLATFORMS, "")

    title_parts = [station]
    if platforms:
        title_parts.append(f"platform {platforms}")
    if via:
        via_str = ", ".join(via) if isinstance(via, list) else str(via)
        if via_str:
            title_parts.append(f"via {via_str}")
    if direction:
        title_parts.append(f"direction {direction}")

    return " ".join(title_parts)


async def async_validate_station_on_url(
    hass, server_url: str, station: str, data_source: str
) -> dict:
    """
    Validate that the station can be reached with the given data source on the specified server URL.
    Returns {"valid": True} or {"valid": False, "error": "description"}
    """
    from urllib.parse import quote

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .const import DATA_SOURCE_MAP, SERVER_URL_FASERF, SERVER_URL_OFFICIAL

    # Clean station name
    station_str: str = str(station)
    # Remove any trailing provider suffix like (MVV) or (IRIS-TTS)
    station_str = re.sub(r"\s+\([^)]+\)$", "", station_str).strip()

    station_cleaned = " ".join(station_str.split())
    encoded_station = quote(station_cleaned, safe="-:")
    if encoded_station.endswith("."):
        encoded_station = encoded_station[:-1] + "%2E"

    url = f"{server_url}/{encoded_station}.json"

    params: dict[str, str] = {}
    if data_source in DATA_SOURCE_MAP:
        key, value = DATA_SOURCE_MAP[data_source].split("=")
        params[key] = value
    elif data_source == "hafas=1":
        params["hafas"] = "1"

    try:
        import aiohttp

        session = async_get_clientsession(hass)
        headers = {
            "User-Agent": "HomeAssistant-DBInfoScreen/2.0 (+https://github.com/FaserF/ha-db_infoscreen)"
        }
        async with session.get(
            url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                if "error" in data:
                    return {
                        "valid": False,
                        "error": data.get("error", "Unknown API error"),
                    }
                if "departures" not in data and "arrivals" not in data:
                    is_german = getattr(hass.config, "language", "en") == "de"
                    if is_german:
                        err_msg = f"Keine Abfahrtsdaten für '{station}' mit Datenquelle '{data_source}' gefunden. Bitte prüfe Stationsname und Datenquelle."
                    else:
                        err_msg = f"No departure data found for '{station}' with data source '{data_source}'. Please check the station name and data source."
                    return {
                        "valid": False,
                        "error": err_msg,
                    }
                return {"valid": True}
            elif response.status == 300:
                return {
                    "valid": False,
                    "ambiguous": True,
                    "error": f"Station '{station}' is ambiguous (Status 300).",
                }
            elif response.status == 404:
                return {
                    "valid": False,
                    "error": f"Station '{station}' not found. Please check the spelling or try a different data source.",
                }
            else:
                return {
                    "valid": False,
                    "error": f"API returned status {response.status}. Please try again later.",
                }
    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Validation request failed: %s", e)
        is_german = getattr(hass.config, "language", "en") == "de"

        # Check if server is FaserF or Official
        is_private = False
        for priv_url in [SERVER_URL_OFFICIAL, SERVER_URL_FASERF]:
            if priv_url.lower() in server_url.lower():
                is_private = True
                break

        if is_private:
            if is_german:
                err_msg = (
                    "Verbindung zum Server fehlgeschlagen. Der FaserF/Official Server ist ein "
                    "privat gehosteter Server. Eine 24/7-Verfügbarkeit kann nicht garantiert "
                    "werden, es wird jedoch versucht. Fehler: "
                )
            else:
                err_msg = (
                    "Connection to server failed. The FaserF/Official server is a privately "
                    "hosted server. 24/7 availability cannot be guaranteed, but we try. "
                    "Error: "
                )
            return {"valid": False, "error": f"{err_msg}{e!s}"}
        else:
            if is_german:
                err_msg = "Verbindung zum API-Server fehlgeschlagen: "
            else:
                err_msg = "Could not connect to API server: "
            return {"valid": False, "error": f"{err_msg}{e!s}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """
    Handle the initial configuration and setup wizard for DB Infoscreen.

    This class manages the multi-step process:
    1. Server selection (user step)
    2. Station search (station_search step)
    3. Station selection/resolve (choose step)
    4. Basic configuration (details step)
    5. Advanced configuration (advanced step)
    6. Manual entry/Data source selection (manual_config step)
    """

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.found_stations: list[str] = []
        self.selected_station: str | None = None
        self.selected_code: str | None = None
        self.no_match: bool = False
        self.is_manual_entry: bool = False
        self.basic_options: dict[str, Any] = {}
        self.server_url: str = ""
        self.server_type: str = SERVER_TYPE_CUSTOM
        self.station_query: str = ""
        self.data_source: str = "IRIS-TTS"
        self._station_map: dict[str, str] = {}
        self.discovery_info: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):
        """
        Handle the first step: Server Selection.
        """
        # Check if we are running in Hass.io
        is_hassio_env = False
        try:
            from homeassistant.components.hassio import is_hassio  # type: ignore

            is_hassio_env = is_hassio(self.hass)  # type: ignore
        except (ImportError, AttributeError):
            _LOGGER.debug("Hass.io component not found or is_hassio missing")

        if (
            user_input is None
            and is_hassio_env
            and not self.context.get("hassio_checked")
            and not self.discovery_info.get(CONF_SERVER_URL)
        ):
            try:
                self._context["hassio_checked"] = True  # type: ignore
            except (AttributeError, TypeError):
                try:
                    self.context["hassio_checked"] = True  # type: ignore
                except (AttributeError, TypeError):
                    pass
            return await self.async_step_hassio()

        errors = {}

        suggested_url = self.discovery_info.get(CONF_SERVER_URL, "")
        suggested_type = self.discovery_info.get(CONF_SERVER_TYPE, SERVER_TYPE_CUSTOM)

        if user_input is not None:
            server_type = user_input.get(CONF_SERVER_TYPE)
            url = ""

            if server_type == SERVER_TYPE_OFFICIAL:
                url = SERVER_URL_OFFICIAL
            elif server_type == SERVER_TYPE_FASERF:
                url = SERVER_URL_FASERF
            else:
                url = user_input.get(CONF_SERVER_URL, "")

            # Ensure URL has protocol
            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            # Remove trailing slash
            url = url.removesuffix("/")

            if not url:
                errors[CONF_SERVER_URL] = "invalid_url"
            else:
                # Availability check
                valid = await self._validate_server_url(url)
                if not valid:
                    if (
                        server_type == SERVER_TYPE_OFFICIAL
                        or "finalrewind" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_official"
                    elif (
                        server_type == SERVER_TYPE_FASERF or "fabiseitz" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_faserf"
                    else:
                        errors["base"] = "cannot_connect"
                else:
                    self.server_url = url
                    self.server_type = server_type
                    return await self.async_step_station_search()

        schema_fields: dict[Any, Any] = {
            vol.Required(CONF_SERVER_TYPE, default=suggested_type): vol.In(
                [SERVER_TYPE_CUSTOM, SERVER_TYPE_OFFICIAL, SERVER_TYPE_FASERF]
            ),
        }
        if suggested_url:
            schema_fields[vol.Optional(CONF_SERVER_URL, default=suggested_url)] = (
                cv.string
            )
        else:
            schema_fields[vol.Optional(CONF_SERVER_URL)] = cv.string

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    async def async_step_station_search(self, user_input=None):
        """
        Handle the station search step.
        """
        errors: dict[str, Any] = {}

        if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
            errors["base"] = "max_sensors_reached"
            return self.async_show_form(
                step_id="station_search",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        if user_input is not None:
            station_query = normalize_whitespace(user_input.get(CONF_STATION))
            data_source = user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")

            # Save state for possible "Go Back"
            self.station_query = station_query
            self.data_source = data_source

            if station_query:
                # Reset transient state
                self.no_match = False
                self.found_stations = []
                self.selected_station = None
                self._station_map = {}

                stations = []
                if data_source == "IRIS-TTS":
                    stations = await async_get_stations(self.hass, self.server_url)
                    if not stations:
                        if (
                            self.server_type == SERVER_TYPE_OFFICIAL
                            or "finalrewind" in self.server_url.lower()
                        ):
                            errors["base"] = "cannot_connect_official"
                        elif (
                            self.server_type == SERVER_TYPE_FASERF
                            or "fabiseitz" in self.server_url.lower()
                        ):
                            errors["base"] = "cannot_connect_faserf"
                        else:
                            errors["base"] = "cannot_connect"
                    else:
                        matches = await self.hass.async_add_executor_job(
                            find_station_matches, stations, station_query
                        )
                        if not matches:
                            self.found_stations = [f"{station_query} (Manual Entry)"]
                            self.no_match = True
                            return await self.async_step_choose()
                        elif (
                            len(matches) == 1
                            and matches[0].lower() == station_query.lower()
                        ):
                            self.selected_station = f"{matches[0]} (IRIS-TTS)"
                            return await self.async_step_details()
                        else:
                            self.found_stations = [f"{m} (IRIS-TTS)" for m in matches]
                            manual_option = f"{station_query} (Manual Entry)"
                            if manual_option not in self.found_stations:
                                self.found_stations.append(manual_option)
                            return await self.async_step_choose()
                else:
                    # Non-IRIS provider: Resolve candidates from server
                    from .utils import async_get_station_candidates

                    candidates = await async_get_station_candidates(
                        self.hass, self.server_url, station_query, data_source
                    )
                    if not candidates:
                        self.found_stations = [f"{station_query} (Manual Entry)"]
                        self.no_match = True
                        # If no results and localized provider, go straight to manual entry
                        # but set a flag so it can show a warning
                        # self.selected_station = f"{station_query} (Manual Entry)"
                        # return await self.async_step_manual_config()
                        return await self.async_step_choose()

                    if (
                        len(candidates) == 1
                        and candidates[0]["name"].lower() == station_query.lower()
                    ):
                        self.selected_station = (
                            f"{candidates[0]['name']} ({data_source})"
                        )
                        self.selected_code = candidates[0]["code"]
                        # Pre-fill data source for next steps
                        self.basic_options[CONF_DATA_SOURCE] = data_source
                        return await self.async_step_details()

                    self.found_stations = []
                    for c in candidates:
                        display_name = f"{c['name']} ({data_source})"
                        self.found_stations.append(display_name)
                        self._station_map[display_name] = c["code"]

                    manual_option = f"{station_query} (Manual Entry)"
                    if manual_option not in self.found_stations:
                        self.found_stations.append(manual_option)
                    return await self.async_step_choose()

        return self.async_show_form(
            step_id="station_search",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION, default=self.station_query): cv.string,
                    vol.Optional(CONF_DATA_SOURCE, default=self.data_source): vol.In(
                        DATA_SOURCE_OPTIONS
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_choose(self, user_input=None):
        """
        Handle the selection step if multiple stations or no matches were found.

        Allows the user to select from a list of matches or proceed with manual entry.
        """
        if user_input is not None and CONF_STATION in user_input:
            self.selected_station = user_input.get(CONF_STATION)
            if self.selected_station == "back":
                return await self.async_step_station_search()

            # Check if user selected manual entry
            if self.selected_station and self.selected_station.endswith(
                " (Manual Entry)"
            ):
                self.is_manual_entry = True
                return await self.async_step_manual_config()

            # Extract data source from selection if present, e.g. "Dörverden (IRIS-TTS)"
            match = re.search(r"\(([^)]+)\)$", self.selected_station)
            if match:
                self.basic_options[CONF_DATA_SOURCE] = match.group(1)

            # Use internal code if we have one in the map
            if self.selected_station in self._station_map:
                self.selected_code = self._station_map[self.selected_station]
            else:
                self.selected_code = None

            return await self.async_step_details()

        if self.no_match:
            return self.async_show_form(
                step_id="choose",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_STATION, default=self.found_stations[0]
                        ): vol.In(
                            {
                                "back": "← Back (Change Search / Data Source)",
                                **{s: s for s in self.found_stations},
                            }
                        )
                    }
                ),
                description_placeholders={
                    "description": "No matching stations found. If your station isn't listed, you can select 'Manual Entry' to configure it manually or go back to try a different search."
                },
                errors={"base": "no_stations_found"},
            )

        return self.async_show_form(
            step_id="choose",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION, default=self.found_stations[0]): vol.In(
                        self.found_stations
                    )
                }
            ),
            description_placeholders={
                "description": "We found several stations matching your search. Please pick the correct one from the list.\n\n**Station not found?** If your station isn't listed, you can select 'Manual Entry' to configure it manually."
            },
        )

    async def async_step_details(self, user_input=None):
        """
        Handle the configuration details step for verified stations.

        Prompts for common settings like update interval and whether to
        proceed to advanced options.
        """
        errors: dict[str, Any] = {}

        if user_input is not None:
            # Save basic options to temporary state
            self.basic_options = user_input

            if user_input.get("advanced"):
                return await self.async_step_advanced()

            # Combine basic options with defaults for entry creation
            entry_data = {CONF_STATION: self.selected_station, **user_input}
            # Remove the virtual "advanced" flag
            entry_data.pop("advanced", None)

            # Check MAX_SENSORS
            if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
                errors["base"] = "max_sensors_reached"
                return self.async_show_form(
                    step_id="details",
                    data_schema=self.details_schema(basic=True),
                    errors=errors,
                    description_placeholders={"station": str(self.selected_station)},
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="details",
            data_schema=self.details_schema(basic=True),
            errors=errors,
            description_placeholders={"station": str(self.selected_station)},
        )

    async def async_step_manual_config(self, user_input=None):
        """
        Handle configuration for manually entered (non-IRIS) stations.

        Prompts for a data source (e.g., ÖBB, SBB) and configuration for
        stations not found in the standard IRIS list.
        """
        errors: dict[str, Any] = {}

        if user_input is not None:
            # Combine with station for entry creation
            entry_data = {CONF_STATION: self.selected_station, **user_input}

            # Check MAX_SENSORS
            if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
                errors["base"] = "max_sensors_reached"
                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=self._manual_config_schema(),
                    errors=errors,
                    description_placeholders={"station": str(self.selected_station)},
                )

            # Validate station before saving
            validation_result = await self._validate_station(
                str(entry_data.get(CONF_STATION, "")),
                str(entry_data.get(CONF_DATA_SOURCE, "IRIS-TTS")),
            )
            if not validation_result["valid"]:
                errors["base"] = (
                    "station_ambiguous"
                    if validation_result.get("ambiguous")
                    else "station_invalid"
                )
                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=self._manual_config_schema(),
                    errors=errors,
                    description_placeholders={
                        "station": str(self.selected_station),
                        "error_detail": validation_result["error"],
                    },
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="manual_config",
            data_schema=self._manual_config_schema(),
            errors=errors,
            description_placeholders={"station": str(self.selected_station)},
        )

    def _manual_config_schema(self):
        """Schema for manual entry configuration with Data Source prominent."""
        return vol.Schema(
            {
                vol.Optional(CONF_DATA_SOURCE, default=self.data_source): vol.In(
                    DATA_SOURCE_OPTIONS
                ),
                vol.Optional(
                    CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES
                ): cv.positive_int,
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_PLATFORMS, default=""): cv.string,
                vol.Optional(CONF_VIA_STATIONS, default=""): cv.string,
                vol.Optional(CONF_VIA_STATIONS_LOGIC, default="OR"): vol.In(
                    ["OR", "AND"]
                ),
            }
        )

    async def async_step_advanced(self, user_input=None):
        """
        Handle advanced configuration options.

        Prompts for filters like train types, route keeping, and custom API URLs.
        """
        errors: dict[str, Any] = {}

        if user_input is not None:
            # Combine all options
            entry_data = {
                CONF_STATION: self.selected_station,
                **self.basic_options,
                **user_input,
            }
            entry_data.pop("advanced", None)

            # Check MAX_SENSORS
            if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
                errors["base"] = "max_sensors_reached"
                return self.async_show_form(
                    step_id="advanced",
                    data_schema=self.details_schema(basic=False),
                    errors=errors,
                    description_placeholders={"station": str(self.selected_station)},
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.details_schema(basic=False),
            errors=errors,
            description_placeholders={"station": str(self.selected_station)},
        )

    async def _async_create_db_entry(self, user_input):
        """
        Finalize the entry creation and save to Home Assistant.
        """
        # Add server URL to data
        user_input[CONF_SERVER_URL] = self.server_url

        # Retrieve the station name/ID. In the details step, it's not in user_input,
        # so we fall back to self.selected_station (what was chosen in Search/Choose step)
        station_id = user_input.get(CONF_STATION) or self.selected_station or ""

        # Remove any provider suffix if present, e.g. "Dörverden (IRIS-TTS)" or "Ferbitzer Weg (BVG)"
        display_name = re.sub(r"\s+\([^)]+\)$", "", str(station_id)).strip()

        # Use the internal code if it was resolved during search
        if hasattr(self, "selected_code") and self.selected_code:
            user_input[CONF_STATION] = self.selected_code
        else:
            user_input[CONF_STATION] = normalize_whitespace(display_name)

        # Validate station data can be retrieved
        station_raw = user_input.get(CONF_STATION, "")
        # Fallback to self.data_source if not in user_input
        ds_raw = user_input.get(CONF_DATA_SOURCE) or getattr(
            self, "data_source", "IRIS-TTS"
        )
        data_source = normalize_data_source(ds_raw)

        # Handle empty deduplication key by reverting to default
        if (
            CONF_DEDUPLICATE_KEY in user_input
            and not str(user_input.get(CONF_DEDUPLICATE_KEY, "")).strip()
        ):
            user_input[CONF_DEDUPLICATE_KEY] = DEFAULT_DEDUPLICATE_KEY

        validation_result = await self._validate_station(station_raw, data_source)
        if not validation_result["valid"]:
            _LOGGER.error(
                "Station validation failed (%s): %s",
                data_source,
                validation_result["error"],
            )
            # Instead of aborting, we return to the appropriate step with an error
            errors = {
                "base": (
                    "station_ambiguous"
                    if validation_result.get("ambiguous")
                    or validation_result.get("error") == "ambiguous"
                    else "station_invalid"
                )
            }

            if self.is_manual_entry:
                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=self._manual_config_schema(),
                    errors=errors,
                    description_placeholders={
                        "station": str(self.selected_station),
                        "error_detail": validation_result["error"],
                    },
                )

            # Fallback for details/advanced steps
            return self.async_show_form(
                step_id="details",
                data_schema=self.details_schema(basic=True),
                errors=errors,
                description_placeholders={
                    "station": str(self.selected_station),
                    "error_detail": validation_result["error"],
                },
            )

        # Process separated via stations into list
        via_raw = user_input.get(CONF_VIA_STATIONS, "")
        if isinstance(via_raw, str):
            user_input[CONF_VIA_STATIONS] = [
                normalize_whitespace(s) for s in re.split(r",|\|", via_raw) if s.strip()
            ]

        user_input[CONF_SERVER_URL] = self.server_url
        user_input[CONF_SERVER_TYPE] = self.server_type
        via = user_input.get(CONF_VIA_STATIONS, [])
        user_input[CONF_VIA_STATIONS] = via
        direction = normalize_whitespace(user_input.get(CONF_DIRECTION, ""))
        user_input[CONF_DIRECTION] = direction
        excluded_directions = user_input.get(CONF_EXCLUDED_DIRECTIONS, "")
        if isinstance(excluded_directions, str):
            excluded_directions = ", ".join(
                [normalize_whitespace(s) for s in excluded_directions.split(",")]
            )
        user_input[CONF_EXCLUDED_DIRECTIONS] = excluded_directions
        platforms = user_input.get(CONF_PLATFORMS, "")
        user_input[CONF_PLATFORMS] = str(platforms).replace(" ", "")
        fav_trains = user_input.get(CONF_FAVORITE_TRAINS, "")
        if isinstance(fav_trains, str):
            user_input[CONF_FAVORITE_TRAINS] = ", ".join(
                [normalize_whitespace(s) for s in fav_trains.split(",")]
            )

        # Ensure we keep the valid data_source correctly tracked for the final entry
        user_input[CONF_DATA_SOURCE] = data_source
        parts = [str(user_input[CONF_STATION])]

        if via:
            parts.append(f"via={','.join(via)}")
        if direction:
            parts.append(f"dir={direction}")
        if platforms:
            parts.append(f"plat={platforms}")
        base_unique_id = "_".join(parts)

        # Check if same station and same data source already exist
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        same_station_entries = [
            e
            for e in existing_entries
            if re.match(rf"^{re.escape(base_unique_id)}(_\d+)?$", e.unique_id or "")
        ]

        for entry in same_station_entries:
            if entry.data.get(CONF_DATA_SOURCE) == data_source:
                await self.async_set_unique_id(entry.unique_id)
                _LOGGER.info(
                    "Aborting: configuration for this station and data source already exists."
                )
                return self.async_abort(reason="already_configured")

        # Find a free unique ID
        suffix = 0
        unique_id_candidate = base_unique_id
        used_ids = {e.unique_id for e in same_station_entries}

        while unique_id_candidate in used_ids:
            suffix += 1
            unique_id_candidate = f"{base_unique_id}_{suffix}"

        await self.async_set_unique_id(unique_id_candidate)
        _LOGGER.debug("Creating new sensor with unique_id: %s", unique_id_candidate)

        # Generate title using the human-readable display name
        full_title = display_name
        # Remove only the provider suffix if it's there
        full_title = re.sub(
            r"\s+\((?:IRIS-TTS|Manual Entry)\)$", "", full_title
        ).strip()

        if same_station_entries:
            full_title += f" ({data_source})"

        return self.async_create_entry(
            title=full_title,
            data=user_input,
        )

    def details_schema(self, basic=True):
        """
        Build the voluptuous Schema used for the integration's details form.
        Does NOT include CONF_STATION as that is already selected.
        """
        if basic:
            return vol.Schema(
                {
                    vol.Optional(
                        CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): cv.positive_int,
                    vol.Optional("advanced", default=False): cv.boolean,
                    vol.Optional(CONF_WALK_TIME, default=0): cv.positive_int,
                    vol.Optional(CONF_PAUSED, default=False): cv.boolean,
                }
            )

        return self._get_advanced_schema(is_options_flow=False)

    def _get_advanced_schema(self, is_options_flow=False):
        """Get the schema for advanced options."""
        schema = {
            vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
            vol.Optional(CONF_DROP_LATE_TRAINS, default=False): cv.boolean,
            vol.Optional(CONF_DEDUPLICATE_DEPARTURES, default=False): cv.boolean,
            vol.Optional(
                CONF_DEDUPLICATE_KEY, default=DEFAULT_DEDUPLICATE_KEY
            ): cv.string,
            vol.Optional(CONF_DETAILED, default=False): cv.boolean,
            vol.Optional(CONF_PAST_60_MINUTES, default=False): cv.boolean,
            vol.Optional(CONF_KEEP_ROUTE, default=False): cv.boolean,
            vol.Optional(CONF_KEEP_ENDSTATION, default=False): cv.boolean,
            vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): cv.string,
            vol.Optional(CONF_PLATFORMS, default=""): cv.string,
            vol.Optional(CONF_VIA_STATIONS, default=""): cv.string,
            vol.Optional(CONF_VIA_STATIONS_LOGIC, default="OR"): vol.In(["OR", "AND"]),
            vol.Optional(CONF_DIRECTION, default=""): cv.string,
            vol.Optional(CONF_EXCLUDED_DIRECTIONS, default=""): cv.string,
            vol.Optional(CONF_FAVORITE_TRAINS, default=""): cv.string,
        }

        # Data source is only editable in Options Flow, as it's already selected
        # in the first step of the Config Flow
        if is_options_flow:
            schema[vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS")] = vol.In(
                DATA_SOURCE_OPTIONS
            )

        return vol.Schema(schema)

    async def _validate_station(self, station: str, data_source: str) -> dict:
        """
        Validate that the station can be reached with the given data source.
        Returns {"valid": True} or {"valid": False, "error": "description"}
        """
        return await async_validate_station_on_url(
            self.hass, self.server_url, station, data_source
        )

    async def _validate_server_url(self, url: str) -> bool:
        """Verify that the server is reachable and looks like a DBF instance."""
        from .utils import async_verify_server

        return await async_verify_server(self.hass, url)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry (station, server, data source)."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            server_type = user_input.get(CONF_SERVER_TYPE, SERVER_TYPE_CUSTOM)
            url = ""

            if server_type == SERVER_TYPE_OFFICIAL:
                url = SERVER_URL_OFFICIAL
            elif server_type == SERVER_TYPE_FASERF:
                url = SERVER_URL_FASERF
            else:
                url = user_input.get(CONF_SERVER_URL, "")

            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            url = url.removesuffix("/")

            if not url:
                errors[CONF_SERVER_URL] = "invalid_url"
            else:
                # Validate server reachability
                from .utils import async_verify_server

                valid_server = await async_verify_server(self.hass, url)
                if not valid_server:
                    if (
                        server_type == SERVER_TYPE_OFFICIAL
                        or "finalrewind" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_official"
                    elif (
                        server_type == SERVER_TYPE_FASERF or "fabiseitz" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_faserf"
                    else:
                        errors["base"] = "cannot_connect"
                else:
                    station_raw = normalize_whitespace(user_input.get(CONF_STATION, ""))
                    ds_raw = user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")
                    data_source = normalize_data_source(ds_raw)

                    validation_result = await async_validate_station_on_url(
                        self.hass, url, station_raw, data_source
                    )
                    if not validation_result["valid"]:
                        errors["base"] = (
                            "station_ambiguous"
                            if validation_result.get("ambiguous")
                            else "station_invalid"
                        )
                    else:
                        data_updates = dict(reconfigure_entry.data)
                        data_updates[CONF_SERVER_TYPE] = server_type
                        data_updates[CONF_SERVER_URL] = url
                        data_updates[CONF_STATION] = station_raw
                        data_updates[CONF_DATA_SOURCE] = data_source

                        return self.async_update_reload_and_abort(
                            reconfigure_entry,
                            data_updates=data_updates,
                        )

        # Pre-fill from existing entry
        existing = reconfigure_entry.data
        current_server_type = existing.get(CONF_SERVER_TYPE, SERVER_TYPE_CUSTOM)
        # Infer server type from URL for backward compat
        current_url = existing.get(CONF_SERVER_URL, "")
        if not current_server_type or current_server_type == SERVER_TYPE_CUSTOM:
            if current_url == SERVER_URL_OFFICIAL:
                current_server_type = SERVER_TYPE_OFFICIAL
            elif current_url == SERVER_URL_FASERF:
                current_server_type = SERVER_TYPE_FASERF

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STATION,
                        default=existing.get(CONF_STATION, ""),
                    ): cv.string,
                    vol.Required(
                        CONF_SERVER_TYPE,
                        default=current_server_type,
                    ): vol.In(
                        [SERVER_TYPE_CUSTOM, SERVER_TYPE_OFFICIAL, SERVER_TYPE_FASERF]
                    ),
                    vol.Optional(
                        CONF_SERVER_URL,
                        default=current_url,
                    ): cv.string,
                    vol.Optional(
                        CONF_DATA_SOURCE,
                        default=existing.get(CONF_DATA_SOURCE, "IRIS-TTS"),
                    ): vol.In(DATA_SOURCE_OPTIONS),
                }
            ),
            errors=errors,
            description_placeholders={
                "station": existing.get(CONF_STATION, ""),
            },
        )

    async def _async_get_addon_manager(self, slug: str) -> Any:
        """Return the addon manager."""
        try:
            from homeassistant.components.hassio import AddonManager

            return AddonManager(self.hass, _LOGGER, slug, ADDON_NAME)
        except (ImportError, AttributeError):
            return None

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle Hass.io discovery."""
        if discovery_info is not None:
            slug = getattr(discovery_info, "slug", None)
            if slug:
                for expected_slug in [ADDON_STABLE_SLUG, ADDON_DEV_SLUG]:
                    if slug == expected_slug or slug.endswith(f"_{expected_slug}"):
                        await self._async_prefill_addon_info(slug)
                        return await self.async_step_user()

        try:
            from homeassistant.components.hassio import AddonState
        except (ImportError, AttributeError):
            return await self.async_step_user()

        # Check if either stable or dev is installed
        for slug in [ADDON_STABLE_SLUG, ADDON_DEV_SLUG]:
            addon_manager = await self._async_get_addon_manager(slug)
            if addon_manager is None:
                continue
            addon_info = await addon_manager.async_get_addon_info()
            if addon_info.state != AddonState.NOT_INSTALLED:
                # Already installed, pre-fill info and go to user step
                await self._async_prefill_addon_info(slug)
                return await self.async_step_user()

        # Neither installed, ask user
        return await self.async_step_hassio_confirm()

    async def _async_prefill_addon_info(self, slug: str) -> None:
        """Pre-fill addon info from Supervisor."""
        addon_manager = await self._async_get_addon_manager(slug)
        try:
            addon_info = await addon_manager.async_get_addon_info()
            # Supervisor hostnames use hyphens, slugs might use underscores
            host = slug.replace("_", "-")
            port = DEFAULT_PORT

            if addon_info.network:
                # Find port for 8092 (internal)
                for internal, external in addon_info.network.items():
                    if internal.startswith(f"{DEFAULT_PORT}/"):
                        port = external
                        break

            self.discovery_info[CONF_SERVER_URL] = f"http://{host}:{port}"
            self.discovery_info[CONF_SERVER_TYPE] = SERVER_TYPE_CUSTOM
            _LOGGER.debug("Pre-filled addon info: %s", self.discovery_info)
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Could not pre-fill addon info: %s", e)

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None):
        """Confirm installation of the official addon."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Install stable addon
            slug = ADDON_STABLE_SLUG
            addon_manager = await self._async_get_addon_manager(slug)
            try:
                await addon_manager.async_install_addon()
                await addon_manager.async_start_addon()
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Failed to install DBF addon (%s): %s", slug, e)
                errors["base"] = "addon_install_error"
                return self.async_show_form(
                    step_id="hassio_confirm",
                    errors=errors,
                )
            # After installation, pre-fill info
            await self._async_prefill_addon_info(slug)
            return await self.async_step_user()

        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"addon_name": ADDON_NAME},
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle zeroconf discovery for DBF add-on."""
        host = discovery_info.host
        port = discovery_info.port

        server_url = f"http://{host}:{port}"
        self.discovery_info[CONF_SERVER_URL] = server_url
        self.discovery_info[CONF_SERVER_TYPE] = SERVER_TYPE_CUSTOM
        self.server_url = server_url
        self.server_type = SERVER_TYPE_CUSTOM

        await self.async_set_unique_id(f"dbf_{host}_{port}")
        self._abort_if_unique_id_configured(updates={CONF_SERVER_URL: server_url})

        try:
            self._context["title_placeholders"] = {"url": server_url}
            self._context["hassio_checked"] = True
        except (AttributeError, TypeError):
            try:
                self.context["title_placeholders"] = {"url": server_url}
                self.context["hassio_checked"] = True
            except (AttributeError, TypeError):
                pass

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm zeroconf discovery and proceed to station search."""
        server_url = self.discovery_info.get(CONF_SERVER_URL, "")

        if user_input is not None:
            self.server_url = server_url
            self.server_type = SERVER_TYPE_CUSTOM
            return await self.async_step_station_search()

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"url": server_url},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """
    Handle post-setup configuration changes for DB Infoscreen.

    Organizes options into categories (General, Filter, Display, Advanced)
    for a cleaner user experience.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._options = dict(config_entry.options)

    async def _async_save_options(self, user_input=None):
        """Update options and the entry title before saving."""
        if user_input:
            # Handle empty deduplication key by reverting to default
            if (
                CONF_DEDUPLICATE_KEY in user_input
                and not str(user_input.get(CONF_DEDUPLICATE_KEY, "")).strip()
            ):
                user_input[CONF_DEDUPLICATE_KEY] = DEFAULT_DEDUPLICATE_KEY

            # Normalize text inputs
            for key in [CONF_DIRECTION, CONF_STATION]:
                if key in user_input:
                    user_input[key] = normalize_whitespace(user_input[key])

            if CONF_PLATFORMS in user_input:
                user_input[CONF_PLATFORMS] = str(user_input[CONF_PLATFORMS]).replace(
                    " ", ""
                )

            if CONF_VIA_STATIONS in user_input:
                via_raw = user_input.get(CONF_VIA_STATIONS, "")
                if isinstance(via_raw, str):
                    user_input[CONF_VIA_STATIONS] = [
                        normalize_whitespace(s)
                        for s in re.split(r",|\|", via_raw)
                        if s.strip()
                    ]
                elif via_raw is None:
                    user_input[CONF_VIA_STATIONS] = []

            for key in [CONF_EXCLUDED_DIRECTIONS, CONF_FAVORITE_TRAINS]:
                if key in user_input:
                    val = user_input[key]
                    if isinstance(val, str):
                        user_input[key] = ", ".join(
                            [normalize_whitespace(s) for s in val.split(",")]
                        )

            self._options.update(user_input)

        # Recalculate title based on merged data and options
        merged_config = {**self._config_entry.data, **self._options}
        new_title = _generate_entry_title(merged_config)

        # Preserve the data source suffix if it was already there
        if f"({merged_config.get(CONF_DATA_SOURCE)})" in self._config_entry.title:
            new_title += f" ({merged_config.get(CONF_DATA_SOURCE)})"

        return self.async_create_entry(title=new_title, data=self._options)

    def _get_config_value(self, key, default=None):
        """Get value from our updated options or fall back to config data."""
        val = self._options.get(key, self._config_entry.data.get(key, default))

        # If it's a template key and currently empty, use the default
        if (
            key in (CONF_DEDUPLICATE_KEY, CONF_TEXT_VIEW_TEMPLATE)
            and not str(val).strip()
        ):
            return default

        # Infer server type if missing or default (for backward compatibility)
        if key == CONF_SERVER_TYPE and (not val or val == SERVER_TYPE_CUSTOM):
            url = self._get_config_value(CONF_SERVER_URL, "")
            if url == SERVER_URL_OFFICIAL:
                return SERVER_TYPE_OFFICIAL
            if url == SERVER_URL_FASERF:
                return SERVER_TYPE_FASERF

        return val

    async def async_step_init(self, user_input=None):
        """
        Handle the options flow menu.

        Displays a list of configuration categories for the user to select.
        """
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general_options",
                "server_options",
                "filter_options",
                "display_options",
                "advanced_options",
                "finish",
            ],
        )

    async def async_step_general_options(self, user_input=None):
        """Handle general options."""
        if user_input is not None:
            return await self._async_save_options(user_input)

        return self.async_show_form(
            step_id="general_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NEXT_DEPARTURES,
                        default=self._get_config_value(
                            CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self._get_config_value(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_CACHE_TTL,
                        default=self._get_config_value(
                            CONF_CACHE_TTL, DEFAULT_CACHE_TTL
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_OFFSET,
                        default=self._get_config_value(CONF_OFFSET, DEFAULT_OFFSET),
                    ): cv.string,
                    vol.Optional(
                        CONF_PAUSED,
                        default=self._get_config_value(CONF_PAUSED, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_WALK_TIME,
                        default=self._get_config_value(CONF_WALK_TIME, 0),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_CALENDAR_EVENT_DURATION,
                        default=self._get_config_value(
                            CONF_CALENDAR_EVENT_DURATION,
                            DEFAULT_CALENDAR_EVENT_DURATION,
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_CALENDAR_ONLY_FAVORITES,
                        default=self._get_config_value(
                            CONF_CALENDAR_ONLY_FAVORITES, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_CALENDAR_ONLY_DELAYED,
                        default=self._get_config_value(
                            CONF_CALENDAR_ONLY_DELAYED, False
                        ),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_server_options(self, user_input=None):
        """Handle server configuration options."""
        errors = {}
        if user_input is not None:
            server_type = user_input.get(CONF_SERVER_TYPE)
            url = ""

            if server_type == SERVER_TYPE_OFFICIAL:
                url = SERVER_URL_OFFICIAL
            elif server_type == SERVER_TYPE_FASERF:
                url = SERVER_URL_FASERF
            else:
                url = user_input.get(CONF_SERVER_URL, "")

            # Ensure URL has protocol
            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            # Remove trailing slash
            url = url.removesuffix("/")

            if not url:
                errors[CONF_SERVER_URL] = "invalid_url"
            else:
                # Availability / Validity check
                from .utils import async_verify_server

                valid = await async_verify_server(self.hass, url)
                if not valid:
                    if (
                        server_type == SERVER_TYPE_OFFICIAL
                        or "finalrewind" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_official"
                    elif (
                        server_type == SERVER_TYPE_FASERF or "fabiseitz" in url.lower()
                    ):
                        errors["base"] = "cannot_connect_faserf"
                    else:
                        errors["base"] = "cannot_connect"
                else:
                    # Validate that the configured station is reachable on the new server URL
                    station_raw = self._get_config_value(CONF_STATION)
                    ds_raw = self._get_config_value(CONF_DATA_SOURCE, "IRIS-TTS")
                    data_source = normalize_data_source(ds_raw)

                    validation_result = await async_validate_station_on_url(
                        self.hass, url, station_raw, data_source
                    )
                    if not validation_result["valid"]:
                        errors["base"] = "station_invalid"
                        return self.async_show_form(
                            step_id="server_options",
                            data_schema=vol.Schema(
                                {
                                    vol.Required(
                                        CONF_SERVER_TYPE,
                                        default=server_type,
                                    ): vol.In(
                                        [
                                            SERVER_TYPE_CUSTOM,
                                            SERVER_TYPE_OFFICIAL,
                                            SERVER_TYPE_FASERF,
                                        ]
                                    ),
                                    vol.Optional(
                                        CONF_SERVER_URL,
                                        default=url,
                                    ): cv.string,
                                }
                            ),
                            errors={"base": "station_invalid"},
                            description_placeholders={
                                "error_detail": validation_result["error"]
                            },
                        )
                    else:
                        # Update options
                        user_input[CONF_SERVER_URL] = url
                        return await self._async_save_options(user_input)

        return self.async_show_form(
            step_id="server_options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERVER_TYPE,
                        default=self._get_config_value(
                            CONF_SERVER_TYPE, SERVER_TYPE_CUSTOM
                        ),
                    ): vol.In(
                        [SERVER_TYPE_CUSTOM, SERVER_TYPE_OFFICIAL, SERVER_TYPE_FASERF]
                    ),
                    vol.Optional(
                        CONF_SERVER_URL,
                        default=self._get_config_value(CONF_SERVER_URL, ""),
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_filter_options(self, user_input=None):
        """Handle filter options."""
        if user_input is not None:
            # Process via_stations from string to list if necessary
            if CONF_VIA_STATIONS in user_input:
                via_raw = user_input.get(CONF_VIA_STATIONS, "")
                if isinstance(via_raw, str):
                    user_input[CONF_VIA_STATIONS] = [
                        s.strip() for s in re.split(r",|\|", via_raw) if s.strip()
                    ]
                elif isinstance(via_raw, list):
                    user_input[CONF_VIA_STATIONS] = [
                        s.strip() for s in via_raw if isinstance(s, str) and s.strip()
                    ]
                elif via_raw is None:
                    user_input[CONF_VIA_STATIONS] = []
            return await self._async_save_options(user_input)

        # Get via_stations list and join for display
        via_stations_list = self._get_config_value(CONF_VIA_STATIONS, [])
        if isinstance(via_stations_list, str):
            via_stations_list = [
                s.strip() for s in re.split(r",|\|", via_stations_list) if s.strip()
            ]
        elif not isinstance(via_stations_list, list):
            via_stations_list = []
        via_stations_str = ", ".join(via_stations_list)

        # Get ignored train types (must be a list for multi_select)
        ignored_types = self._get_config_value(CONF_IGNORED_TRAINTYPES, [])
        if isinstance(ignored_types, str):
            ignored_types = [t.strip() for t in ignored_types.split(",") if t.strip()]

        schema = vol.Schema(
            {
                vol.Optional(CONF_PLATFORMS): cv.string,
                vol.Optional(CONF_VIA_STATIONS): cv.string,
                vol.Optional(CONF_VIA_STATIONS_LOGIC): vol.In(["OR", "AND"]),
                vol.Optional(CONF_DIRECTION): cv.string,
                vol.Optional(CONF_EXCLUDED_DIRECTIONS): cv.string,
                vol.Optional(CONF_IGNORED_TRAINTYPES): cv.multi_select(
                    IGNORED_TRAINTYPES_OPTIONS
                ),
                vol.Optional(CONF_EXCLUDE_CANCELLED): cv.boolean,
                vol.Optional(CONF_FAVORITE_TRAINS): cv.string,
            }
        )

        return self.async_show_form(
            step_id="filter_options",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                {
                    CONF_PLATFORMS: self._get_config_value(CONF_PLATFORMS, ""),
                    CONF_VIA_STATIONS: via_stations_str,
                    CONF_VIA_STATIONS_LOGIC: self._get_config_value(
                        CONF_VIA_STATIONS_LOGIC, "OR"
                    ),
                    CONF_DIRECTION: self._get_config_value(CONF_DIRECTION, ""),
                    CONF_EXCLUDED_DIRECTIONS: self._get_config_value(
                        CONF_EXCLUDED_DIRECTIONS, ""
                    ),
                    CONF_IGNORED_TRAINTYPES: ignored_types,
                    CONF_EXCLUDE_CANCELLED: self._get_config_value(
                        CONF_EXCLUDE_CANCELLED, False
                    ),
                    CONF_FAVORITE_TRAINS: self._get_config_value(
                        CONF_FAVORITE_TRAINS, ""
                    ),
                },
            ),
        )

    async def async_step_display_options(self, user_input=None):
        """Handle display options."""
        if user_input is not None:
            return await self._async_save_options(user_input)

        return self.async_show_form(
            step_id="display_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DETAILED,
                        default=self._get_config_value(CONF_DETAILED, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ENABLE_TEXT_VIEW,
                        default=self._get_config_value(CONF_ENABLE_TEXT_VIEW, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_TEXT_VIEW_TEMPLATE,
                        default=self._get_config_value(
                            CONF_TEXT_VIEW_TEMPLATE, DEFAULT_TEXT_VIEW_TEMPLATE
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_ADMODE,
                        default=self._get_config_value(
                            CONF_ADMODE, "preferred departure"
                        ),
                    ): vol.In(["preferred departure", "arrival", "departure"]),
                    vol.Optional(
                        CONF_HIDE_LOW_DELAY,
                        default=self._get_config_value(CONF_HIDE_LOW_DELAY, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_SHOW_OCCUPANCY,
                        default=self._get_config_value(CONF_SHOW_OCCUPANCY, False),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_advanced_options(self, user_input=None):
        """Handle advanced options."""
        errors = {}
        if user_input is not None:
            new_data_source = user_input.get(CONF_DATA_SOURCE)
            if new_data_source:
                station_raw = self._get_config_value(CONF_STATION)
                url = self._get_config_value(CONF_SERVER_URL, "")
                data_source = normalize_data_source(new_data_source)

                validation_result = await async_validate_station_on_url(
                    self.hass, url, station_raw, data_source
                )
                if not validation_result["valid"]:
                    errors["base"] = "station_invalid"
                    return self.async_show_form(
                        step_id="advanced_options",
                        data_schema=vol.Schema(
                            {
                                vol.Optional(
                                    CONF_DEDUPLICATE_DEPARTURES,
                                    default=user_input.get(
                                        CONF_DEDUPLICATE_DEPARTURES, False
                                    ),
                                ): cv.boolean,
                                vol.Optional(
                                    CONF_DEDUPLICATE_KEY,
                                    default=user_input.get(
                                        CONF_DEDUPLICATE_KEY, DEFAULT_DEDUPLICATE_KEY
                                    ),
                                ): cv.string,
                                vol.Optional(
                                    CONF_KEEP_ROUTE,
                                    default=user_input.get(CONF_KEEP_ROUTE, False),
                                ): cv.boolean,
                                vol.Optional(
                                    CONF_KEEP_ENDSTATION,
                                    default=user_input.get(CONF_KEEP_ENDSTATION, False),
                                ): cv.boolean,
                                vol.Optional(
                                    CONF_DROP_LATE_TRAINS,
                                    default=user_input.get(
                                        CONF_DROP_LATE_TRAINS, False
                                    ),
                                ): cv.boolean,
                                vol.Optional(
                                    CONF_PAST_60_MINUTES,
                                    default=user_input.get(CONF_PAST_60_MINUTES, False),
                                ): cv.boolean,
                                vol.Optional(
                                    CONF_DATA_SOURCE,
                                    default=new_data_source,
                                ): vol.In(DATA_SOURCE_OPTIONS),
                            }
                        ),
                        errors={"base": "station_invalid"},
                        description_placeholders={
                            "error_detail": validation_result["error"]
                        },
                    )
            return await self._async_save_options(user_input)

        return self.async_show_form(
            step_id="advanced_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEDUPLICATE_DEPARTURES,
                        default=self._get_config_value(
                            CONF_DEDUPLICATE_DEPARTURES, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DEDUPLICATE_KEY,
                        default=self._get_config_value(
                            CONF_DEDUPLICATE_KEY, DEFAULT_DEDUPLICATE_KEY
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_KEEP_ROUTE,
                        default=self._get_config_value(CONF_KEEP_ROUTE, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_KEEP_ENDSTATION,
                        default=self._get_config_value(CONF_KEEP_ENDSTATION, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DROP_LATE_TRAINS,
                        default=self._get_config_value(CONF_DROP_LATE_TRAINS, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_PAST_60_MINUTES,
                        default=self._get_config_value(CONF_PAST_60_MINUTES, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DATA_SOURCE,
                        default=self._get_config_value(CONF_DATA_SOURCE, "IRIS-TTS"),
                    ): vol.In(DATA_SOURCE_OPTIONS),
                }
            ),
            errors=errors,
        )

    async def async_step_finish(self, user_input=None):
        """Finish and save the options."""
        return await self._async_save_options()

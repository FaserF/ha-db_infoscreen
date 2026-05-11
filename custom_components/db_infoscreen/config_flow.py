"""Config flow for DB Infoscreen integration."""

import logging
import re
import voluptuous as vol
from typing import Any
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .const import (
    CONF_PAUSED,
    DOMAIN,
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_OFFSET,
    MAX_SENSORS,
    CONF_HIDE_LOW_DELAY,
    CONF_DETAILED,
    CONF_PAST_60_MINUTES,
    CONF_DATA_SOURCE,
    CONF_OFFSET,
    CONF_PLATFORMS,
    CONF_ADMODE,
    DATA_SOURCE_OPTIONS,
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
    CONF_ENABLE_TEXT_VIEW,
    CONF_TEXT_VIEW_TEMPLATE,
    DEFAULT_TEXT_VIEW_TEMPLATE,
    CONF_EXCLUDE_CANCELLED,
    CONF_SHOW_OCCUPANCY,
    CONF_FAVORITE_TRAINS,
    CONF_VIA_STATIONS_LOGIC,
    IGNORED_TRAINTYPES_OPTIONS,
    CONF_WALK_TIME,
    CONF_SERVER_TYPE,
    CONF_SERVER_URL,
    SERVER_TYPE_CUSTOM,
    SERVER_TYPE_OFFICIAL,
    SERVER_TYPE_FASERF,
    SERVER_URL_OFFICIAL,
    SERVER_URL_FASERF,
    normalize_data_source,
)
from .utils import async_get_stations, find_station_matches, normalize_whitespace

_LOGGER = logging.getLogger(__name__)


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

    async def async_step_user(self, user_input=None):
        """
        Handle the first step: Server Selection.
        """
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
            if url.endswith("/"):
                url = url[:-1]

            if not url:
                errors[CONF_SERVER_URL] = "invalid_url"
            else:
                # Availability check
                valid = await self._validate_server_url(url)
                if not valid:
                    errors["base"] = "cannot_connect"
                else:
                    self.server_url = url
                    self.server_type = server_type
                    return await self.async_step_station_search()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERVER_TYPE, default=SERVER_TYPE_CUSTOM): vol.In(
                        [SERVER_TYPE_CUSTOM, SERVER_TYPE_OFFICIAL, SERVER_TYPE_FASERF]
                    ),
                    vol.Optional(CONF_SERVER_URL): cv.string,
                }
            ),
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
                        errors["base"] = "cannot_connect"
                    else:
                        matches = find_station_matches(stations, station_query)
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
        from urllib.parse import quote
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        from .const import DATA_SOURCE_MAP

        # Clean station name
        station_str: str = str(station)
        # Remove any trailing provider suffix like (MVV) or (IRIS-TTS)
        station_str = re.sub(r"\s+\([^)]+\)$", "", station_str).strip()

        station_cleaned = " ".join(station_str.split())
        encoded_station = quote(station_cleaned, safe="-:")

        base_url = self.server_url
        url = f"{base_url}/{encoded_station}.json"

        params: dict[str, str] = {}
        if data_source in DATA_SOURCE_MAP:
            key, value = DATA_SOURCE_MAP[data_source].split("=")
            params[key] = value
        elif data_source == "hafas=1":
            params["hafas"] = "1"

        try:
            import aiohttp

            session = async_get_clientsession(self.hass)
            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "error" in data:
                        return {
                            "valid": False,
                            "error": data.get("error", "Unknown API error"),
                        }
                    if "departures" not in data and "arrivals" not in data:
                        return {
                            "valid": False,
                            "error": f"No departure data found for '{station}' with data source '{data_source}'. Please check the station name and data source.",
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
        except Exception as e:
            _LOGGER.error("Validation request failed: %s", e)
            return {"valid": False, "error": f"Could not connect to API: {str(e)}"}

        return {"valid": False, "error": "Unknown verification error"}

    async def _validate_server_url(self, url: str) -> bool:
        """Verify that the server is reachable and looks like a DBF instance."""
        from .utils import async_verify_server

        return await async_verify_server(self.hass, url)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


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

        if new_title != self._config_entry.title:
            self.hass.config_entries.async_update_entry(
                self._config_entry, title=new_title
            )

        return self.async_create_entry(title="", data=self._options)

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
            if url.endswith("/"):
                url = url[:-1]

            if not url:
                errors[CONF_SERVER_URL] = "invalid_url"
            else:
                # Availability / Validity check
                from .utils import async_verify_server

                valid = await async_verify_server(self.hass, url)
                if not valid:
                    errors["base"] = "cannot_connect"
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
                user_input[CONF_VIA_STATIONS] = [
                    s.strip() for s in re.split(r",|\|", via_raw) if s.strip()
                ]
            return await self._async_save_options(user_input)

        # Get via_stations list and join for display
        via_stations_list = self._get_config_value(CONF_VIA_STATIONS, [])
        if via_stations_list is None:
            via_stations_list = []
        via_stations_str = ", ".join(via_stations_list)

        # Get ignored train types (must be a list for multi_select)
        ignored_types = self._get_config_value(CONF_IGNORED_TRAINTYPES, [])
        if isinstance(ignored_types, str):
            ignored_types = [t.strip() for t in ignored_types.split(",") if t.strip()]

        return self.async_show_form(
            step_id="filter_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PLATFORMS,
                        default=self._get_config_value(CONF_PLATFORMS, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_VIA_STATIONS,
                        default=via_stations_str,
                    ): cv.string,
                    vol.Optional(
                        CONF_VIA_STATIONS_LOGIC,
                        default=self._get_config_value(CONF_VIA_STATIONS_LOGIC, "OR"),
                    ): vol.In(["OR", "AND"]),
                    vol.Optional(
                        CONF_DIRECTION,
                        default=self._get_config_value(CONF_DIRECTION, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_EXCLUDED_DIRECTIONS,
                        default=self._get_config_value(CONF_EXCLUDED_DIRECTIONS, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_IGNORED_TRAINTYPES,
                        default=ignored_types,
                    ): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
                    vol.Optional(
                        CONF_EXCLUDE_CANCELLED,
                        default=self._get_config_value(CONF_EXCLUDE_CANCELLED, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_FAVORITE_TRAINS,
                        default=self._get_config_value(CONF_FAVORITE_TRAINS, ""),
                    ): cv.string,
                }
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
        if user_input is not None:
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
        )

    async def async_step_finish(self, user_input=None):
        """Finish and save the options."""
        return await self._async_save_options()

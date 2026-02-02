import logging
import re
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .const import (
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
    CONF_CUSTOM_API_URL,
    CONF_DATA_SOURCE,
    CONF_OFFSET,
    CONF_PLATFORMS,
    CONF_ADMODE,
    DATA_SOURCE_OPTIONS,
    CONF_VIA_STATIONS,
    CONF_DIRECTION,
    CONF_EXCLUDED_DIRECTIONS,
    CONF_IGNORED_TRAINTYPES,
    IGNORED_TRAINTYPES_OPTIONS,
    CONF_DROP_LATE_TRAINS,
    CONF_KEEP_ROUTE,
    CONF_KEEP_ENDSTATION,
    CONF_DEDUPLICATE_DEPARTURES,
    CONF_ENABLE_TEXT_VIEW,
    CONF_EXCLUDE_CANCELLED,
    CONF_SHOW_OCCUPANCY,
    normalize_data_source,
)
from .utils import async_get_stations, find_station_matches

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.found_stations = []
        self.selected_station = None
        self.no_match = False
        self.is_manual_entry = False
        self.basic_options = {}

    async def async_step_user(self, user_input=None):
        """
        Handle the initial step: Search for a station.
        """
        errors = {}

        if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
            errors["base"] = "max_sensors_reached"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        if user_input is not None:
            station_query = user_input.get(CONF_STATION)
            if station_query:
                # Reset transient state to avoid stale data affecting subsequent flows
                self.no_match = False
                self.found_stations = []
                self.selected_station = None

                stations = await async_get_stations(self.hass)
                if not stations:
                    errors["base"] = "cannot_connect"
                else:
                    matches = find_station_matches(stations, station_query)
                    if not matches:
                        # No matches found, but allow manual entry via choose step
                        self.found_stations = [f"{station_query} (Manual Entry)"]
                        self.no_match = True
                        return await self.async_step_choose(user_input=None)
                    elif (
                        len(matches) == 1
                        and matches[0].lower() == station_query.lower()
                    ):
                        # Exact unique match, proceed to details
                        self.selected_station = f"{matches[0]} (IRIS-TTS)"
                        return await self.async_step_details()
                    else:
                        # Multiple or fuzzy matches, let user choose
                        self.found_stations = [f"{m} (IRIS-TTS)" for m in matches]
                        # Append manual entry option if not already in list
                        manual_option = f"{station_query} (Manual Entry)"
                        if manual_option not in self.found_stations:
                            self.found_stations.append(manual_option)
                        return await self.async_step_choose()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_STATION): cv.string}),
            errors=errors,
        )

    async def async_step_choose(self, user_input=None):
        """
        Handle the selection step if multiple stations were found.
        """
        if user_input is not None:
            self.selected_station = user_input[CONF_STATION]
            # Check if user selected manual entry
            if self.selected_station.endswith(" (Manual Entry)"):
                self.is_manual_entry = True
                return await self.async_step_manual_config()
            return await self.async_step_details()

        if self.no_match:
            return self.async_show_form(
                step_id="choose",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_STATION, default=self.found_stations[0]
                        ): vol.In(self.found_stations)
                    }
                ),
                description_placeholders={
                    "warning": "⚠️ Station not found in official IRIS list! Please verify spelling."
                },
                errors={"base": "station_not_found_warning"},
            )

        return self.async_show_form(
            step_id="choose",
            data_schema=vol.Schema(
                {vol.Required(CONF_STATION): vol.In(self.found_stations)}
            ),
        )

    async def async_step_details(self, user_input=None):
        """
        Handle the configuration details step.
        """
        errors = {}

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
                    description_placeholders={"station": self.selected_station},
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="details",
            data_schema=self.details_schema(basic=True),
            errors=errors,
            description_placeholders={"station": self.selected_station},
        )

    async def async_step_manual_config(self, user_input=None):
        """
        Handle configuration for manually entered (non-IRIS) stations.
        Data Source is shown prominently here.
        """
        errors = {}

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
                    description_placeholders={"station": self.selected_station},
                )

            # Validate station before saving
            validation_result = await self._validate_station(
                entry_data.get(CONF_STATION),
                entry_data.get(CONF_DATA_SOURCE, "IRIS-TTS"),
                entry_data.get(CONF_CUSTOM_API_URL, ""),
            )
            if not validation_result["valid"]:
                errors["base"] = "station_invalid"
                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=self._manual_config_schema(),
                    errors=errors,
                    description_placeholders={
                        "station": self.selected_station,
                        "error_detail": validation_result["error"],
                    },
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="manual_config",
            data_schema=self._manual_config_schema(),
            errors=errors,
            description_placeholders={"station": self.selected_station},
        )

    def _manual_config_schema(self):
        """Schema for manual entry configuration with Data Source prominent."""
        return vol.Schema(
            {
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(
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
                vol.Optional(CONF_CUSTOM_API_URL, default=""): cv.string,
            }
        )

    async def async_step_advanced(self, user_input=None):
        """
        Handle advanced configuration options.
        """
        errors = {}

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
                    description_placeholders={"station": self.selected_station},
                )

            return await self._async_create_db_entry(entry_data)

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.details_schema(basic=False),
            errors=errors,
            description_placeholders={"station": self.selected_station},
        )

    async def _async_create_db_entry(self, user_input):
        """Finalize the entry creation logic merged from upstream."""
        # Validate station data can be retrieved
        station_raw = user_input.get(CONF_STATION, "")
        data_source = normalize_data_source(
            user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")
        )
        custom_api_url = user_input.get(CONF_CUSTOM_API_URL, "")

        validation_result = await self._validate_station(
            station_raw, data_source, custom_api_url
        )
        if not validation_result["valid"]:
            _LOGGER.error("Station validation failed: %s", validation_result["error"])
            # Return to appropriate step with error
            return self.async_abort(reason="station_validation_failed")

        # Process separated via stations into list
        via_raw = user_input.get(CONF_VIA_STATIONS, "")
        if isinstance(via_raw, str):
            user_input[CONF_VIA_STATIONS] = [
                s.strip() for s in re.split(r",|\|", via_raw) if s.strip()
            ]

        station = user_input[CONF_STATION]
        # Remove (IRIS-TTS) or (Manual Entry) suffix if present for ID and URL
        if station.endswith(" (IRIS-TTS)"):
            station = station[: -len(" (IRIS-TTS)")].strip()
        elif station.endswith(" (Manual Entry)"):
            station = station[: -len(" (Manual Entry)")].strip()

        user_input[CONF_STATION] = station
        via = user_input.get(CONF_VIA_STATIONS, [])
        user_input[CONF_VIA_STATIONS] = via
        direction = user_input.get(CONF_DIRECTION, "")
        user_input[CONF_DIRECTION] = direction
        platforms = user_input.get(CONF_PLATFORMS, "")
        user_input[CONF_PLATFORMS] = platforms
        data_source = user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")
        user_input[CONF_DATA_SOURCE] = data_source
        parts = [station]

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

        title_parts = [station]
        if platforms:
            title_parts.append(f"platform {platforms}")
        if via:
            title_parts.append(f"via {' '.join(via)}")
        if direction:
            title_parts.append(f"direction {direction}")
        if same_station_entries:
            title_parts.append(f"({data_source})")

        full_title = " ".join(title_parts)

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
                }
            )

        return vol.Schema(
            {
                vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
                vol.Optional(CONF_DROP_LATE_TRAINS, default=False): cv.boolean,
                vol.Optional(CONF_DEDUPLICATE_DEPARTURES, default=False): cv.boolean,
                vol.Optional(CONF_DETAILED, default=False): cv.boolean,
                vol.Optional(CONF_PAST_60_MINUTES, default=False): cv.boolean,
                vol.Optional(CONF_KEEP_ROUTE, default=False): cv.boolean,
                vol.Optional(CONF_KEEP_ENDSTATION, default=False): cv.boolean,
                vol.Optional(CONF_CUSTOM_API_URL, default=""): cv.string,
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(
                    DATA_SOURCE_OPTIONS
                ),
                vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): cv.string,
                vol.Optional(CONF_PLATFORMS, default=""): cv.string,
                vol.Optional(CONF_VIA_STATIONS, default=""): cv.string,
                vol.Optional(CONF_DIRECTION, default=""): cv.string,
            }
        )

    async def _validate_station(
        self, station: str, data_source: str, custom_api_url: str = ""
    ) -> dict:
        """
        Validate that the station can be reached with the given data source.
        Returns {"valid": True} or {"valid": False, "error": "description"}
        """
        from urllib.parse import quote, urlencode
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        from .const import DATA_SOURCE_MAP

        # Clean station name
        if station.endswith(" (IRIS-TTS)"):
            station = station[: -len(" (IRIS-TTS)")].strip()
        elif station.endswith(" (Manual Entry)"):
            station = station[: -len(" (Manual Entry)")].strip()

        station_cleaned = " ".join(station.split())
        encoded_station = quote(station_cleaned, safe=",-")

        base_url = custom_api_url if custom_api_url else "https://dbf.finalrewind.org"
        url = f"{base_url}/{encoded_station}.json"

        params = {}
        if data_source in DATA_SOURCE_MAP:
            key, value = DATA_SOURCE_MAP[data_source].split("=")
            params[key] = value
        elif data_source == "hafas=1":
            params["hafas"] = "1"

        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, timeout=10) as response:
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

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._options = dict(config_entry.options)

    def _get_config_value(self, key, default=None):
        """Get value from our updated options or fall back to config data."""
        return self._options.get(key, self._config_entry.data.get(key, default))

    async def async_step_init(self, user_input=None):
        """Handle the options flow menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general_options",
                "filter_options",
                "display_options",
                "advanced_options",
                "finish",
            ],
        )

    async def async_step_general_options(self, user_input=None):
        """Handle general options."""
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

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
                }
            ),
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
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        # Get via_stations list and join for display
        via_stations_list = self._get_config_value(CONF_VIA_STATIONS, [])
        if via_stations_list is None:
            via_stations_list = []
        via_stations_str = ", ".join(via_stations_list)

        # Get ignored train types
        ignored_types = self._get_config_value(CONF_IGNORED_TRAINTYPES, [])
        if ignored_types is None:
            ignored_types = []

        default_ignored = [
            "Unbekannter Zugtyp" if t == "" else t for t in ignored_types
        ]

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
                        CONF_DIRECTION,
                        default=self._get_config_value(CONF_DIRECTION, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_EXCLUDED_DIRECTIONS,
                        default=self._get_config_value(CONF_EXCLUDED_DIRECTIONS, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_IGNORED_TRAINTYPES,
                        default=default_ignored,
                    ): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
                    vol.Optional(
                        CONF_EXCLUDE_CANCELLED,
                        default=self._get_config_value(CONF_EXCLUDE_CANCELLED, False),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_display_options(self, user_input=None):
        """Handle display options."""
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

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
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="advanced_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CUSTOM_API_URL,
                        default=self._get_config_value(CONF_CUSTOM_API_URL, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_DEDUPLICATE_DEPARTURES,
                        default=self._get_config_value(
                            CONF_DEDUPLICATE_DEPARTURES, False
                        ),
                    ): cv.boolean,
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
        return self.async_create_entry(title="", data=self._options)

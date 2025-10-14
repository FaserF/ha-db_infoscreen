import logging
import re
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_UPDATE_INTERVAL, DEFAULT_OFFSET, MAX_SENSORS,
    CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES, CONF_CUSTOM_API_URL,
    CONF_DATA_SOURCE, CONF_OFFSET, CONF_PLATFORMS, CONF_ADMODE, DATA_SOURCE_OPTIONS,
    CONF_VIA_STATIONS, CONF_DIRECTION, CONF_IGNORED_TRAINTYPES, IGNORED_TRAINTYPES_OPTIONS,
    CONF_DROP_LATE_TRAINS, CONF_KEEP_ROUTE, CONF_KEEP_ENDSTATION, CONF_DEDUPLICATE_DEPARTURES
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """
        Handle the initial user step of the config flow: validate input, normalize fields, ensure uniqueness, and create or abort a config entry.

        Parameters:
        	user_input (dict|None): Form data from the user. Expected keys include:
        		- CONF_STATION: station identifier (required when provided)
        		- CONF_VIA_STATIONS: comma-separated string of intermediate stations
        		- CONF_DIRECTION: optional direction string
        		- CONF_PLATFORMS: optional platform specification
        		- CONF_DATA_SOURCE: optional data source identifier (defaults to "IRIS-TTS")
        		- CONF_CUSTOM_API_URL: optional custom API URL (bypasses MAX_SENSORS limit when present)

        Description:
        	- If user_input is None, shows the user form with the configured data schema.
        	- If provided, enforces the MAX_SENSORS limit unless a custom API URL is supplied.
        	- Normalizes CONF_VIA_STATIONS into a list of trimmed station strings.
        	- Builds a base unique ID from station, via stations, direction, and platforms.
        	- If an existing entry for the same station and data source exists, aborts the flow with reason "already_configured".
        	- Otherwise, selects an unused unique ID (appending a numeric suffix if needed), sets it for the flow, and creates a new config entry.
        	- The created entry's title is derived from station, platforms, via stations, direction, and includes the data source only when multiple entries exist for the station.

        Returns:
        	flow_result: The flow result that either shows the form, aborts the flow, or creates a new configuration entry.
        """
        errors = {}

        if user_input is not None:
            # Check MAX_SENSORS only if no custom API URL is provided
            if not user_input.get(CONF_CUSTOM_API_URL):
                if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
                    errors["base"] = "max_sensors_reached"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self.data_schema(),
                        errors=errors,
                    )

            # Process comma-separated via stations into list
            via_raw = user_input.get(CONF_VIA_STATIONS, "")
            user_input[CONF_VIA_STATIONS] = [
                s.strip() for s in via_raw.split(",") if s.strip()
            ]

            # Build base unique ID from station, via stations, direction, and platforms
            station     = user_input[CONF_STATION]
            via         = user_input[CONF_VIA_STATIONS]
            direction   = user_input.get(CONF_DIRECTION, "")
            platforms   = user_input[CONF_PLATFORMS]
            data_source = user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")
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
                e for e in existing_entries
                if re.match(fr"^{re.escape(base_unique_id)}(_\d+)?$", e.unique_id or "")
            ]

            for entry in same_station_entries:
                if entry.data.get(CONF_DATA_SOURCE) == data_source:
                    await self.async_set_unique_id(entry.unique_id)
                    _LOGGER.info("Aborting: configuration for this station and data source already exists.")
                    return self.async_abort(reason="already_configured")

            # Find a free unique ID by appending a numeric suffix if needed
            suffix = 1
            unique_id_candidate = base_unique_id
            used_ids = {e.unique_id for e in same_station_entries}

            while unique_id_candidate in used_ids:
                suffix += 1
                unique_id_candidate = f"{base_unique_id}_{suffix}"

            await self.async_set_unique_id(unique_id_candidate)
            _LOGGER.debug("Creating new sensor with unique_id: %s", unique_id_candidate)

            # Build display title (append data source only if there are multiple for this station)
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

        return self.async_show_form(
            step_id="user",
            data_schema=self.data_schema(),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    def data_schema(self):
        """
        Build the voluptuous Schema used for the integration's user configuration form.

        The schema defines all configuration fields presented to the user and their defaults,
        including station selection, polling and display options, data source selection,
        platforms, via stations, direction, and ignored train types.

        Returns:
            vol.Schema: A Voluptuous schema mapping configuration keys to validators and defaults.
        """
        return vol.Schema(
            {
                vol.Required(CONF_STATION): cv.string,
                vol.Optional(CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES): cv.positive_int,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
                vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
                vol.Optional(CONF_DROP_LATE_TRAINS, default=False): cv.boolean,
                vol.Optional(CONF_DEDUPLICATE_DEPARTURES, default=False): cv.boolean,
                vol.Optional(CONF_DETAILED, default=False): cv.boolean,
                vol.Optional(CONF_PAST_60_MINUTES, default=False): cv.boolean,
                vol.Optional(CONF_KEEP_ROUTE, default=False): cv.boolean,
                vol.Optional(CONF_KEEP_ENDSTATION, default=False): cv.boolean,
                vol.Optional(CONF_CUSTOM_API_URL, default=""): cv.string,
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(DATA_SOURCE_OPTIONS),
                vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): cv.string,
                vol.Optional(CONF_PLATFORMS, default=""): cv.string,
                vol.Optional(CONF_ADMODE, default="preferred departure"): vol.In(["preferred departure", "arrival", "departure"]),
                vol.Optional(CONF_VIA_STATIONS, default=""): cv.string,
                vol.Optional(CONF_DIRECTION, default=""): cv.string,
                vol.Optional(CONF_IGNORED_TRAINTYPES, default=[]): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
            }
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """
        Handle the options flow initial step for the integration.

        If `user_input` is provided, normalize `CONF_VIA_STATIONS` from a comma-separated string into a list of trimmed, non-empty station strings and create an options entry using the processed data. If `user_input` is None, show a form whose schema exposes all configurable options with defaults taken from the existing config entry's options or module defaults.

        Returns:
            A flow result representing the created options entry when input was submitted, or the form to display when no input was provided.
        """
        if user_input is not None:
            # Process comma-separated via stations into list
            via_raw = user_input.get(CONF_VIA_STATIONS, "")
            user_input[CONF_VIA_STATIONS] = [
                s.strip() for s in via_raw.split(",") if s.strip()
            ]
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NEXT_DEPARTURES,
                        default=self.config_entry.options.get(
                            CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_HIDE_LOW_DELAY,
                        default=self.config_entry.options.get(
                            CONF_HIDE_LOW_DELAY, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DROP_LATE_TRAINS,
                        default=self.config_entry.options.get(
                            CONF_DROP_LATE_TRAINS, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DEDUPLICATE_DEPARTURES,
                        default=self.config_entry.options.get(
                            CONF_DEDUPLICATE_DEPARTURES, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DETAILED,
                        default=self.config_entry.options.get(CONF_DETAILED, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_PAST_60_MINUTES,
                        default=self.config_entry.options.get(
                            CONF_PAST_60_MINUTES, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_KEEP_ROUTE,
                        default=self.config_entry.options.get(CONF_KEEP_ROUTE, False),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_KEEP_ENDSTATION,
                        default=self.config_entry.options.get(
                            CONF_KEEP_ENDSTATION, False
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_CUSTOM_API_URL,
                        default=self.config_entry.options.get(CONF_CUSTOM_API_URL, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_DATA_SOURCE,
                        default=self.config_entry.options.get(
                            CONF_DATA_SOURCE, "IRIS-TTS"
                        ),
                    ): vol.In(DATA_SOURCE_OPTIONS),
                    vol.Optional(
                        CONF_OFFSET,
                        default=self.config_entry.options.get(CONF_OFFSET, DEFAULT_OFFSET),
                    ): cv.string,
                    vol.Optional(
                        CONF_PLATFORMS,
                        default=self.config_entry.options.get(CONF_PLATFORMS, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_ADMODE,
                        default=self.config_entry.options.get(
                            CONF_ADMODE, "preferred departure"
                        ),
                    ): vol.In(["preferred departure", "arrival", "departure"]),
                    vol.Optional(
                        CONF_VIA_STATIONS,
                        default=", ".join(
                            self.config_entry.options.get(CONF_VIA_STATIONS, [])
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_DIRECTION,
                        default=self.config_entry.options.get(CONF_DIRECTION, ""),
                    ): cv.string,
                    vol.Optional(
                        CONF_IGNORED_TRAINTYPES,
                        default=self.config_entry.options.get(
                            CONF_IGNORED_TRAINTYPES, []
                        ),
                    ): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
                }
            ),
        )
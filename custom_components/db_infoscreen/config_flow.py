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
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors = {}

        if user_input is not None:
            # Check MAX_SENSORS only if no custom API URL is provided
            if not user_input.get(CONF_CUSTOM_API_URL):
                if len(self.hass.config_entries.async_entries(DOMAIN)) >= MAX_SENSORS:
                    errors["base"] = "max_sensors_reached"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self.user_data_schema(),
                        errors=errors,
                    )

            # Process separated via stations into list
            via_raw = user_input.get(CONF_VIA_STATIONS, "")
            user_input[CONF_VIA_STATIONS] = [
                s.strip() for s in via_raw.split("|") if s.strip()
            ]

            # Build base unique ID from station, via stations, direction, and platforms
            station = user_input[CONF_STATION]
            via = user_input[CONF_VIA_STATIONS]
            direction = user_input.get(CONF_DIRECTION, "")
            platforms = user_input.get(CONF_PLATFORMS, "")
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
            suffix = 1
            unique_id_candidate = base_unique_id
            used_ids = {e.unique_id for e in same_station_entries}

            while unique_id_candidate in used_ids:
                suffix += 1
                unique_id_candidate = f"{base_unique_id}_{suffix}"

            await self.async_set_unique_id(unique_id_candidate)
            _LOGGER.debug("Creating new sensor with unique_id: %s", unique_id_candidate)

            # Build display title
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
            data_schema=self.user_data_schema(),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    def user_data_schema(self):
        """Build the schema for the initial user step (simplified)."""
        return vol.Schema(
            {
                vol.Required(CONF_STATION): cv.string,
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(
                    DATA_SOURCE_OPTIONS
                ),
                vol.Optional(
                    CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES
                ): cv.positive_int,
                vol.Optional(CONF_PLATFORMS, default=""): cv.string,
                vol.Optional(CONF_VIA_STATIONS, default=""): cv.string,
                vol.Optional(CONF_DIRECTION, default=""): cv.string,
            }
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle the options flow menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general_options",
                "filter_options",
                "display_options",
                "advanced_options",
            ],
        )

    async def async_step_general_options(self, user_input=None):
        """Handle general options."""
        if user_input is not None:
            return self.async_update_options(user_input)

        return self.async_show_form(
            step_id="general_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NEXT_DEPARTURES,
                        default=self._config_entry.options.get(
                            CONF_NEXT_DEPARTURES,
                            self._config_entry.data.get(
                                CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES
                            ),
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_UPDATE_INTERVAL,
                            self._config_entry.data.get(
                                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                            ),
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_OFFSET,
                        default=self._config_entry.options.get(
                            CONF_OFFSET,
                            self._config_entry.data.get(CONF_OFFSET, DEFAULT_OFFSET),
                        ),
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
                    s.strip() for s in via_raw.split("|") if s.strip()
                ]
            return self.async_update_options(user_input)

        return self.async_show_form(
            step_id="filter_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PLATFORMS,
                        default=self._config_entry.options.get(
                            CONF_PLATFORMS,
                            self._config_entry.data.get(CONF_PLATFORMS, ""),
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_VIA_STATIONS,
                        default="| ".join(
                            self._config_entry.options.get(
                                CONF_VIA_STATIONS,
                                self._config_entry.data.get(CONF_VIA_STATIONS, []),
                            )
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_DIRECTION,
                        default=self._config_entry.options.get(
                            CONF_DIRECTION,
                            self._config_entry.data.get(CONF_DIRECTION, ""),
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_EXCLUDED_DIRECTIONS,
                        default=self._config_entry.options.get(
                            CONF_EXCLUDED_DIRECTIONS,
                            self._config_entry.data.get(CONF_EXCLUDED_DIRECTIONS, ""),
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_IGNORED_TRAINTYPES,
                        default=self._config_entry.options.get(
                            CONF_IGNORED_TRAINTYPES,
                            self._config_entry.data.get(CONF_IGNORED_TRAINTYPES, []),
                        ),
                    ): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
                }
            ),
        )

    async def async_step_display_options(self, user_input=None):
        """Handle display options."""
        if user_input is not None:
            return self.async_update_options(user_input)

        return self.async_show_form(
            step_id="display_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DETAILED,
                        default=self._config_entry.options.get(
                            CONF_DETAILED,
                            self._config_entry.data.get(CONF_DETAILED, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ENABLE_TEXT_VIEW,
                        default=self._config_entry.options.get(
                            CONF_ENABLE_TEXT_VIEW,
                            self._config_entry.data.get(CONF_ENABLE_TEXT_VIEW, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ADMODE,
                        default=self._config_entry.options.get(
                            CONF_ADMODE,
                            self._config_entry.data.get(
                                CONF_ADMODE, "preferred departure"
                            ),
                        ),
                    ): vol.In(["preferred departure", "arrival", "departure"]),
                    vol.Optional(
                        CONF_HIDE_LOW_DELAY,
                        default=self._config_entry.options.get(
                            CONF_HIDE_LOW_DELAY,
                            self._config_entry.data.get(CONF_HIDE_LOW_DELAY, False),
                        ),
                    ): cv.boolean,
                }
            ),
        )

    async def async_step_advanced_options(self, user_input=None):
        """Handle advanced options."""
        if user_input is not None:
            return self.async_update_options(user_input)

        return self.async_show_form(
            step_id="advanced_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CUSTOM_API_URL,
                        default=self._config_entry.options.get(
                            CONF_CUSTOM_API_URL,
                            self._config_entry.data.get(CONF_CUSTOM_API_URL, ""),
                        ),
                    ): cv.string,
                    vol.Optional(
                        CONF_DEDUPLICATE_DEPARTURES,
                        default=self._config_entry.options.get(
                            CONF_DEDUPLICATE_DEPARTURES,
                            self._config_entry.data.get(
                                CONF_DEDUPLICATE_DEPARTURES, False
                            ),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_KEEP_ROUTE,
                        default=self._config_entry.options.get(
                            CONF_KEEP_ROUTE,
                            self._config_entry.data.get(CONF_KEEP_ROUTE, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_KEEP_ENDSTATION,
                        default=self._config_entry.options.get(
                            CONF_KEEP_ENDSTATION,
                            self._config_entry.data.get(CONF_KEEP_ENDSTATION, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DROP_LATE_TRAINS,
                        default=self._config_entry.options.get(
                            CONF_DROP_LATE_TRAINS,
                            self._config_entry.data.get(CONF_DROP_LATE_TRAINS, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_PAST_60_MINUTES,
                        default=self._config_entry.options.get(
                            CONF_PAST_60_MINUTES,
                            self._config_entry.data.get(CONF_PAST_60_MINUTES, False),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DATA_SOURCE,
                        default=self._config_entry.options.get(
                            CONF_DATA_SOURCE,
                            self._config_entry.data.get(CONF_DATA_SOURCE, "IRIS-TTS"),
                        ),
                    ): vol.In(DATA_SOURCE_OPTIONS),
                }
            ),
        )

    def async_update_options(self, user_input):
        """Helper to update options."""
        new_options = self._config_entry.options.copy()
        new_options.update(user_input)
        return self.async_create_entry(title="", data=new_options)

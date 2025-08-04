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
    CONF_VIA_STATIONS, CONF_IGNORED_TRAINTYPES, IGNORED_TRAINTYPES_OPTIONS,
    CONF_DROP_LATE_TRAINS, CONF_KEEP_ROUTE, CONF_KEEP_ENDSTATION
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the user input step."""
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

            # Build base unique ID from station, via stations, and platforms
            station     = user_input[CONF_STATION]
            via         = user_input[CONF_VIA_STATIONS]
            platforms   = user_input[CONF_PLATFORMS]
            data_source = user_input.get(CONF_DATA_SOURCE, "IRIS-TTS")

            parts = [station]
            if via:
                parts.extend(via)
            if platforms:
                parts.extend(platforms)
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
                title_parts.append(f"platform {' '.join(platforms)}")
            if via:
                title_parts.append(f"via {' '.join(via)}")
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

    def data_schema(self):
        """Define the input schema for the user form."""
        return vol.Schema(
            {
                vol.Required(CONF_STATION): cv.string,
                vol.Optional(CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES): cv.positive_int,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
                vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
                vol.Optional(CONF_DROP_LATE_TRAINS, default=False): cv.boolean,
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
                vol.Optional(CONF_IGNORED_TRAINTYPES, default=[]): cv.multi_select(IGNORED_TRAINTYPES_OPTIONS),
            }
        )

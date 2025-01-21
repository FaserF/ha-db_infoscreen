import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_UPDATE_INTERVAL, DEFAULT_OFFSET, MAX_SENSORS,
    CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES, CONF_CUSTOM_API_URL, 
    CONF_DATA_SOURCE, CONF_OFFSET, CONF_PLATFORMS, CONF_ADMODE, DATA_SOURCE_OPTIONS
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if CONF_CUSTOM_API_URL is empty before checking MAX_SENSORS
            custom_api_url = user_input.get(CONF_CUSTOM_API_URL, "")
            if not custom_api_url:
                existing_entries = self.hass.config_entries.async_entries(DOMAIN)
                if len(existing_entries) >= MAX_SENSORS:
                    errors["base"] = "max_sensors_reached"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self.data_schema(),
                        errors=errors
                    )

            unique_id = user_input[CONF_STATION]
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            _LOGGER.debug("Initialized new sensor with station: %s", unique_id)

            return self.async_create_entry(
                title=user_input[CONF_STATION], 
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.data_schema(),
            errors=errors,
        )

    def data_schema(self):
        return vol.Schema(
            {
                vol.Required(CONF_STATION): cv.string,
                vol.Optional(CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES): cv.positive_int,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
                vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
                vol.Optional(CONF_DETAILED, default=False): cv.boolean,
                vol.Optional(CONF_PAST_60_MINUTES, default=False): cv.boolean,
                vol.Optional(CONF_CUSTOM_API_URL, default=""): cv.string,
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(DATA_SOURCE_OPTIONS),
                vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): cv.string,
                vol.Optional(CONF_PLATFORMS, default=""): cv.string,
                vol.Optional(CONF_ADMODE, default="preferred departure"): vol.In(["preferred departure", "arrival", "departure"]),
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry.entry_id)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow"""

    def __init__(self, config_entry_id: str) -> None:
        """Initialize options flow."""
        self.config_entry_id = config_entry_id

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        config_entry = self.hass.config_entries.async_get_entry(self.config_entry_id)
        current_options = config_entry.options or config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NEXT_DEPARTURES, default=current_options.get(CONF_NEXT_DEPARTURES, DEFAULT_NEXT_DEPARTURES)): cv.positive_int,
                    vol.Optional(CONF_UPDATE_INTERVAL, default=current_options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): cv.positive_int,
                    vol.Optional(CONF_HIDE_LOW_DELAY, default=current_options.get(CONF_HIDE_LOW_DELAY, False)): cv.boolean,
                    vol.Optional(CONF_DETAILED, default=current_options.get(CONF_DETAILED, False)): cv.boolean,
                    vol.Optional(CONF_PAST_60_MINUTES, default=current_options.get(CONF_PAST_60_MINUTES, False)): cv.boolean,
                    vol.Optional(CONF_CUSTOM_API_URL, default=current_options.get(CONF_CUSTOM_API_URL, "")): cv.string,
                    vol.Optional(CONF_DATA_SOURCE, default=current_options.get(CONF_DATA_SOURCE, "IRIS-TTS")): vol.In(DATA_SOURCE_OPTIONS),
                    vol.Optional(CONF_OFFSET, default=current_options.get(CONF_OFFSET, DEFAULT_OFFSET)): cv.string,
                    vol.Optional(CONF_PLATFORMS, default=current_options.get(CONF_PLATFORMS, "")): cv.string,
                    vol.Optional(CONF_ADMODE, default="preferred departure"): vol.In(["preferred departure", "arrival", "departure"]),
                }
            ),
        )

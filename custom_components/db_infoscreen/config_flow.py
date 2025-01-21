import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_UPDATE_INTERVAL, DEFAULT_OFFSET, MAX_SENSORS,
    CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES, CONF_CUSTOM_API_URL, CONF_DATA_SOURCE, CONF_OFFSET
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
            # Ensure unique_id is set and check if it's already configured
            unique_id = user_input[CONF_STATION]
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            _LOGGER.debug("Initialized new sensor with station: %s", unique_id)

            return self.async_create_entry(
                title=user_input[CONF_STATION], 
                data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_STATION): cv.string,
                vol.Optional(CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES): cv.positive_int,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
                vol.Optional(CONF_HIDE_LOW_DELAY, default=False): cv.boolean,
                vol.Optional(CONF_DETAILED, default=False): cv.boolean,
                vol.Optional(CONF_PAST_60_MINUTES, default=False): cv.boolean,
                vol.Optional(CONF_CUSTOM_API_URL, default=""): cv.string,
                vol.Optional(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(["IRIS-TTS", "MVV", "ÖBB"]),
                vol.Optional(CONF_OFFSET, default=DEFAULT_OFFSET): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # Do not store the config_entry directly in the constructor anymore
        self.config_entry = None
        self._config_entry_id = config_entry.entry_id

    async def async_step_init(
        self, user_input=None,
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Retrieve current options values from config_entry.data or config_entry.options
        config_entry = self.hass.config_entries.async_get_entry(self._config_entry_id)  # Retrieve config entry by id
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
                    vol.Optional(CONF_DATA_SOURCE, default=current_options.get(CONF_DATA_SOURCE, "IRIS-TTS")): vol.In(["IRIS-TTS", "MVV", "ÖBB"]),
                    vol.Optional(CONF_OFFSET, default=current_options.get(CONF_OFFSET, DEFAULT_OFFSET)): cv.string,
                }
            ),
        )

from homeassistant import config_entries
import voluptuous as vol

from .const import (
    DOMAIN, CONF_STATION, CONF_NEXT_DEPARTURES, CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES, DEFAULT_UPDATE_INTERVAL, MIN_UPDATE_INTERVAL, MAX_SENSORS,
    CONF_HIDE_LOW_DELAY, CONF_DETAILED, CONF_PAST_60_MINUTES, CONF_CUSTOM_API_URL
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if len(self._async_current_entries()) >= MAX_SENSORS:
                errors["base"] = "max_sensors_reached"
            else:
                return self.async_create_entry(title=user_input[CONF_STATION], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_STATION): str,
            vol.Optional(CONF_NEXT_DEPARTURES, default=DEFAULT_NEXT_DEPARTURES): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL)),
            vol.Optional(CONF_HIDE_LOW_DELAY, default=False): bool,
            vol.Optional(CONF_DETAILED, default=False): bool,
            vol.Optional(CONF_PAST_60_MINUTES, default=False): bool,
            vol.Optional(CONF_CUSTOM_API_URL, default=""): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

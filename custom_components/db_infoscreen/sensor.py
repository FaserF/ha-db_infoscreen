from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_CUSTOM_API_URL
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class DBInfoSensor(SensorEntity):
    def __init__(self, coordinator, station):
        self.coordinator = coordinator
        self.station = station
        self._attr_name = f"{station} Departures"
        self._attr_unique_id = f"departures_{station}"
        self._attr_icon = "mdi:train"

        _LOGGER.debug("DBInfoSensor initialized for station: %s", station)

    @property
    def native_value(self):
        if self.coordinator.data:
            scheduledDeparture = self.coordinator.data[0].get("scheduledDeparture", "Unknown")
            _LOGGER.debug("Sensor state updated: %s", scheduledDeparture)
            return scheduledDeparture
        else:
            _LOGGER.warning("No data received for station: %s", self.station)
            return "No Data"

    @property
    def extra_state_attributes(self):
        custom_api_url = self.coordinator.config_entry.data.get(CONF_CUSTOM_API_URL, "")
        attribution = f"Data provided by {custom_api_url}" if custom_api_url else "Data provided by dbf.finalrewind.org API"
        return {
            "next_departures": self.coordinator.data or [],
            "station": self.station,
            "last_updated": self.coordinator.last_update.isoformat() if self.coordinator.last_update else "Unknown",
            "attribution": attribution,
        }

    @property
    def available(self):
        return self.coordinator.last_update_success if hasattr(self.coordinator, "last_update_success") else False

    async def async_update(self):
        _LOGGER.debug("Sensor update triggered but not forcing refresh.")

    async def async_added_to_hass(self):
        _LOGGER.debug("Sensor added to Home Assistant for station: %s", self.station)
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        _LOGGER.debug("Listener attached for station: %s", self.station)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    station = config_entry.data.get("station")
    _LOGGER.debug("Setting up DBInfoSensor for station: %s", station)
    async_add_entities([DBInfoSensor(coordinator, station)])

from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_CUSTOM_API_URL
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

MAX_LENGTH = 70

class DBInfoSensor(SensorEntity):
    def __init__(self, coordinator, station, via_stations):
        self.coordinator = coordinator
        self.station = station
        self.via_stations = via_stations

        via_suffix_name = f" via {' '.join(via_stations)}" if via_stations else ""
        self._attr_name = f"{station} Departures{via_suffix_name}"

        if len(self._attr_name) > MAX_LENGTH:
            self._attr_name = self._attr_name[:MAX_LENGTH]

        via_suffix_id = (
            f"_via_{'_'.join([station[:4] for station in via_stations])}" if via_stations else ""
        )
        self._attr_unique_id = f"departures_{station}{via_suffix_id}".lower().replace(" ", "_")

        if len(self._attr_unique_id) > MAX_LENGTH:
            self._attr_unique_id = self._attr_unique_id[:MAX_LENGTH]

        self._attr_icon = "mdi:train"

        _LOGGER.debug(
            "DBInfoSensor initialized for station: %s, via_stations: %s, unique_id: %s, name: %s",
            station,
            via_stations,
            self._attr_unique_id,
            self._attr_name,
        )

    @property
    def native_value(self):
        if self.coordinator.data:
            departure_time = (
                self.coordinator.data[0].get("scheduledDeparture")
                or self.coordinator.data[0].get("scheduledTime")
                or "Unknown"
            )
            if isinstance(departure_time, int):  # Unix timestamp case
                departure_time = datetime.fromtimestamp(departure_time)
            _LOGGER.debug("Sensor state updated: %s", departure_time)
            return departure_time
        else:
            _LOGGER.warning("No data received for station: %s, via_stations: %s", self.station, self.via_stations)
            return "No Data"

    @property
    def extra_state_attributes(self):
        full_api_url = getattr(self.coordinator, "api_url", "dbf.finalrewind.org")
        attribution = f"Data provided by API {full_api_url}"
        return {
            "next_departures": self.coordinator.data or [],
            "station": self.station,
            "via_stations": self.via_stations,
            "last_updated": self.coordinator.last_update.isoformat() if self.coordinator.last_update else "Unknown",
            "attribution": attribution,
        }

    @property
    def available(self):
        return self.coordinator.last_update_success if hasattr(self.coordinator, "last_update_success") else False

    async def async_update(self):
        _LOGGER.debug("Sensor update triggered but not forcing refresh.")

    async def async_added_to_hass(self):
        _LOGGER.debug("Sensor added to Home Assistant for station: %s, via_stations: %s", self.station, self.via_stations)
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        _LOGGER.debug("Listener attached for station: %s, via_stations: %s", self.station, self.via_stations)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    station = config_entry.data.get("station")
    via_stations = config_entry.data.get("via_stations", [])

    _LOGGER.debug("Setting up DBInfoSensor for station: %s with via_stations: %s", station, via_stations)
    async_add_entities([DBInfoSensor(coordinator, station, via_stations)])

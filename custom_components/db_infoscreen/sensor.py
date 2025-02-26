from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_CUSTOM_API_URL
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

MAX_LENGTH = 70

class DBInfoSensor(SensorEntity):
    def __init__(self, coordinator, station, via_stations, platforms):
        self.coordinator = coordinator
        self.station = station
        self.via_stations = via_stations
        self.platforms = platforms

        platforms_suffix_name = f" platform {' '.join(platforms)}" if platforms else ""
        via_suffix_name = f" via {' '.join(via_stations)}" if via_stations else ""
        self._attr_name = f"{station} Departures{platforms_suffix_name}{via_suffix_name}"

        if len(self._attr_name) > MAX_LENGTH:
            self._attr_name = self._attr_name[:MAX_LENGTH]

        via_suffix_id = (
            f"_via_{'_'.join([station[:4] for station in via_stations])}" if via_stations else ""
        )
        platforms_suffix_id = (
            f"_platform_{'_'.join([platforms for platform in platforms])}" if platforms else ""
        )
        self._attr_unique_id = f"departures_{station}{platforms_suffix_id}{via_suffix_id}".lower().replace(" ", "_")

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

    def format_departure_time(self, departure_time):
        if departure_time is None:
            _LOGGER.debug("Departure time is None")
            return None

        if isinstance(departure_time, int):  # Unix timestamp case
            departure_time = datetime.fromtimestamp(departure_time)
            _LOGGER.debug("Converted departure time from timestamp: %s", departure_time)

        elif isinstance(departure_time, str):
            try:
                departure_time = datetime.strptime(departure_time, "%Y-%m-%d %H:%M:%S")
                _LOGGER.debug("Converted departure time from string: %s", departure_time)
            except ValueError:
                try:
                    departure_time = datetime.strptime(f"{datetime.now().date()} {departure_time}", "%Y-%m-%d %H:%M")
                    _LOGGER.debug("Converted departure time from time string: %s", departure_time)
                except ValueError:
                    _LOGGER.warning("Unable to parse departure time from string: %s", departure_time)
                    return None

        if isinstance(departure_time, datetime):
            _LOGGER.debug("Checking departure time date: %s", departure_time.date())
            _LOGGER.debug("Today's date: %s", datetime.now().date())
            if departure_time.date() != datetime.now().date():
                return departure_time.strftime("%Y-%m-%d %H:%M")
            else:
                return departure_time.strftime("%H:%M")
        else:
            _LOGGER.warning("Invalid departure time: %s", departure_time)
            return None

    @property
    def native_value(self):
        if self.coordinator.data:
            departure_time = self.coordinator.data[0].get("scheduledDeparture") or self.coordinator.data[0].get("scheduledArrival") or self.coordinator.data[0].get("scheduledTime") or self.coordinator.data[0].get("datetime")
            delay_departure = self.coordinator.data[0].get("delayDeparture") or self.coordinator.data[0].get("delay", 0)

            _LOGGER.debug("Raw departure time: %s", departure_time)

            departure_time = self.format_departure_time(departure_time)
            if departure_time is None:
                _LOGGER.debug("Formatted departure time is None, skipping update.")
                return "Invalid Time"

            _LOGGER.debug("Formatted departure time: %s", departure_time)

            if delay_departure == 0:
                _LOGGER.debug("Sensor state updated: %s", departure_time)
                return departure_time
            else:
                departure_time_with_delay = departure_time
                if delay_departure:
                    departure_time_with_delay = f"{departure_time} +{delay_departure}"
                _LOGGER.debug("Sensor state updated with delay: %s", departure_time_with_delay)
                return departure_time_with_delay
        else:
            _LOGGER.warning("No data received for station: %s, via_stations: %s", self.station, self.via_stations)
            return "No Data"

    @property
    def extra_state_attributes(self):
        full_api_url = getattr(self.coordinator, "api_url", "dbf.finalrewind.org")
        attribution = f"Data provided by API {full_api_url}"

        next_departures = self.coordinator.data or []
        for departure in next_departures:
            if 'scheduledTime' in departure and isinstance(departure['scheduledTime'], int):
                departure['scheduledTime'] = datetime.fromtimestamp(departure['scheduledTime']).strftime('%Y-%m-%d %H:%M:%S')
            if 'time' in departure and isinstance(departure['time'], int):
                departure['time'] = datetime.fromtimestamp(departure['time']).strftime('%Y-%m-%d %H:%M:%S')

        last_updated = getattr(self.coordinator, "last_update", None)
        if last_updated:
            last_updated = last_updated.isoformat()
        else:
            last_updated = "Unknown"

        return {
            "next_departures": next_departures,
            "station": self.station,
            "via_stations": self.via_stations,
            "last_updated": last_updated,
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
    platforms = config_entry.data.get("platforms", [])

    _LOGGER.debug("Setting up DBInfoSensor for station: %s with via_stations: %s", station, via_stations)
    async_add_entities([DBInfoSensor(coordinator, station, via_stations, platforms)])
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, CONF_CUSTOM_API_URL
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

MAX_LENGTH = 70


class DBInfoSensor(SensorEntity):
    def __init__(
        self, coordinator, config_entry, station, via_stations, direction, platforms
    ):
        """
        Initialize the DBInfoSensor for a specific station's departure display.

        Constructs the entity name from station, optional platforms, via_stations, and direction (truncating to 70 characters), sets a unique_id based on the config entry, sets a train icon, initializes the last-valid value cache, and logs initialization details.

        Parameters:
                coordinator: Data update coordinator providing sensor data and metadata.
                config_entry: Config entry containing entry_id and stored config.
                station (str): Station name used in the sensor display name.
                via_stations (list[str] | None): Intermediate stations to include in the display name.
                direction (str | None): Direction suffix to include in the display name.
                platforms (str | None): Platform information to include in the display name.
        """
        self.coordinator = coordinator
        self.config_entry = config_entry
        self.station = station
        self.via_stations = via_stations
        self.direction = direction
        self.platforms = platforms

        platforms_suffix_name = f" platform {platforms}" if platforms else ""
        via_suffix_name = f" via {' '.join(via_stations)}" if via_stations else ""
        direction_suffix_name = f" direction {self.direction}" if self.direction else ""
        self._attr_name = f"{station} Departures{platforms_suffix_name}{via_suffix_name}{direction_suffix_name}"

        if len(self._attr_name) > MAX_LENGTH:
            self._attr_name = self._attr_name[:MAX_LENGTH]

        # Use config entry ID as guaranteed-unique sensor ID
        self._attr_unique_id = f"db_infoscreen_{config_entry.entry_id}"
        self._attr_icon = "mdi:train"

        # Initialize _last_valid_value in case there is no valid data initially
        self._last_valid_value = None

        _LOGGER.debug(
            "DBInfoSensor initialized for station: %s, via_stations: %s, direction: %s, unique_id: %s, name: %s",
            station,
            via_stations,
            direction,
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
                _LOGGER.debug(
                    "Converted departure time from string: %s", departure_time
                )
            except ValueError:
                try:
                    departure_time = datetime.strptime(
                        f"{datetime.now().date()} {departure_time}", "%Y-%m-%d %H:%M"
                    )
                    _LOGGER.debug(
                        "Converted departure time from time string: %s", departure_time
                    )
                except ValueError:
                    _LOGGER.warning(
                        "Unable to parse departure time from string: %s", departure_time
                    )
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
        # Check if there is data and if it is valid
        if self.coordinator.data:
            try:
                # Try to get the scheduled departure time
                departure_time = (
                    self.coordinator.data[0].get("scheduledDeparture")
                    or self.coordinator.data[0].get("sched_dep")
                    or self.coordinator.data[0].get("scheduledArrival")
                    or self.coordinator.data[0].get("sched_arr")
                    or self.coordinator.data[0].get("scheduledTime")
                    or self.coordinator.data[0].get("dep")
                    or self.coordinator.data[0].get("datetime")
                )

                # Get the delay in departure, if available
                delay_departure = (
                    self.coordinator.data[0].get("delayDeparture")
                    or self.coordinator.data[0].get("dep_delay")
                    or self.coordinator.data[0].get("delay", 0)
                )

                _LOGGER.debug("Raw departure time: %s", departure_time)

                # Format the departure time if it's valid
                departure_time = self.format_departure_time(departure_time)
                if departure_time is None:
                    _LOGGER.debug("Formatted departure time is None, skipping update.")
                    # If the time is not valid, return the last valid value or "Invalid Time"
                    return self._last_valid_value or "Invalid Time"

                # If there is no delay, update the last valid value with the departure time
                if delay_departure in (0, None, "None"):
                    self._last_valid_value = departure_time
                else:
                    # If there is a delay, append the delay to the departure time
                    departure_time = f"{departure_time} +{delay_departure}"
                    self._last_valid_value = departure_time

                _LOGGER.debug("Sensor state updated: %s", self._last_valid_value)
                return self._last_valid_value
            except Exception as e:
                # Log the error if there is an issue with data parsing
                _LOGGER.error("Exception during data parsing: %s", e)
                # In case of error, return the last valid value or "Error"
                return self._last_valid_value or "Error"
        else:
            # If no new data is available, return the last valid value or a fallback value
            if self._last_valid_value:
                _LOGGER.warning(
                    "No data received for station: %s, via_stations: %s. Keeping previous value: %s.",
                    self.station,
                    self.via_stations,
                    self._last_valid_value,
                )
                return self._last_valid_value
            else:
                # If no data and no previous valid value, return a fallback message
                _LOGGER.warning(
                    "No data received for station: %s, via_stations: %s. No previous value available.",
                    self.station,
                    self.via_stations,
                )
                return "No Data"

    @property
    def extra_state_attributes(self):
        """
        Return additional state attributes for the sensor including next departures and metadata.

        Converts any integer epoch values found in each departure's 'scheduledTime' or 'time' to
        'YYYY-MM-DD HH:MM:SS' strings. Builds an attribution string from the coordinator's
        `api_url` (defaults to "dbf.finalrewind.org") and formats the coordinator's `last_update`
        as an ISO timestamp or "Unknown" if not present.

        Returns:
            dict: A mapping containing:
                - "next_departures": list of departure dicts (with epoch times converted to strings when applicable)
                - "station": configured station identifier
                - "via_stations": configured via stations string or list
                - "direction": configured direction value
                - "last_updated": ISO-formatted last update timestamp or "Unknown"
                - "attribution": attribution string for the data source
        """
        full_api_url = getattr(self.coordinator, "api_url", "dbf.finalrewind.org")
        attribution = f"Data provided by API {full_api_url}"

        # Create a deep copy or new list of dicts to avoid mutating the coordinator data
        raw_departures = self.coordinator.data or []
        next_departures = []

        for departure in raw_departures:
            # Create a shallow copy of the departure so we can modify fields for display
            # without affecting the cached data in the coordinator.
            dep_copy = departure.copy()

            if "scheduledTime" in dep_copy and isinstance(
                dep_copy["scheduledTime"], int
            ):
                dep_copy["scheduledTime"] = datetime.fromtimestamp(
                    dep_copy["scheduledTime"]
                ).strftime("%Y-%m-%d %H:%M:%S")
            if "time" in dep_copy and isinstance(dep_copy["time"], int):
                dep_copy["time"] = datetime.fromtimestamp(dep_copy["time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            next_departures.append(dep_copy)

        last_updated = getattr(self.coordinator, "last_update", None)
        if last_updated:
            last_updated = last_updated.isoformat()
        else:
            last_updated = "Unknown"

        return {
            "next_departures": next_departures,
            "station": self.station,
            "via_stations": self.via_stations,
            "direction": self.direction,
            "last_updated": last_updated,
            "attribution": attribution,
        }

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            if hasattr(self.coordinator, "last_update_success")
            else False
        )

    async def async_update(self):
        _LOGGER.debug("Sensor update triggered but not forcing refresh.")

    async def async_added_to_hass(self):
        _LOGGER.debug(
            "Sensor added to Home Assistant for station: %s, via_stations: %s",
            self.station,
            self.via_stations,
        )
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
        _LOGGER.debug(
            "Listener attached for station: %s, via_stations: %s",
            self.station,
            self.via_stations,
        )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up a DBInfoSensor entity for the given config entry.

    Reads 'station', 'via_stations', 'direction', and 'platforms' from config_entry.data, retrieves the coordinator from hass.data[DOMAIN][config_entry.entry_id], and adds a single DBInfoSensor via async_add_entities.
    """
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    station = config_entry.data.get("station")
    via_stations = config_entry.data.get("via_stations", [])
    direction = config_entry.data.get("direction", "")
    platforms = config_entry.data.get("platforms", "")

    _LOGGER.debug(
        "Setting up DBInfoSensor for station: %s with via_stations: %s and direction: %s",
        station,
        via_stations,
        direction,
    )
    async_add_entities(
        [
            DBInfoSensor(
                coordinator, config_entry, station, via_stations, direction, platforms
            )
        ]
    )

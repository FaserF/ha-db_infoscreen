"""Sensor platform for DB Infoscreen integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from typing import Any
from .const import DOMAIN, CONF_ENABLE_TEXT_VIEW, CONF_STATION, CONF_WALK_TIME
from .entity import DBInfoScreenBaseEntity
import logging
from homeassistant.util import dt as dt_util
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

MAX_LENGTH = 70


class DBInfoSensor(DBInfoScreenBaseEntity, SensorEntity):
    """
    Main sensor for displaying next departures at a station.

    Supports optional filtering by platform, via stations, and direction.
    Can also display a formatted text view for simple displays.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        config_entry,
        station,
        via_stations,
        direction,
        platforms,
        enable_text_view,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self.via_stations = via_stations
        self.direction = direction
        self.platforms = platforms
        self.enable_text_view = enable_text_view

        platforms_suffix_name = f" platform {platforms}" if platforms else ""
        via_suffix_name = f" via {' '.join(via_stations)}" if via_stations else ""
        direction_suffix_name = f" direction {self.direction}" if self.direction else ""

        # Use simple name for entity matching _attr_has_entity_name=True
        self._attr_name = (
            f"Departures{platforms_suffix_name}{via_suffix_name}{direction_suffix_name}"
        )

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
        """
        Format a departure time string or timestamp into a readable HH:MM string.

        Handles various formats (Unix, ISO, HH:MM) and accounts for midnight
        rollover. Returns YYYY-MM-DD HH:MM if the departure is not today.
        """
        if departure_time is None:
            _LOGGER.debug("Departure time is None")
            return None

        now = dt_util.now()
        today = now.date()

        if isinstance(departure_time, (int, float)):  # Unix timestamp case
            departure_time = dt_util.utc_from_timestamp(int(departure_time)).astimezone(
                now.tzinfo
            )
            _LOGGER.debug("Converted departure time from timestamp: %s", departure_time)

        elif isinstance(departure_time, str):
            # Attempt robust parsing using HA helper
            parsed_dt = dt_util.parse_datetime(departure_time)
            if parsed_dt:
                if parsed_dt.tzinfo is None:
                    departure_time = now.replace(
                        year=parsed_dt.year,
                        month=parsed_dt.month,
                        day=parsed_dt.day,
                        hour=parsed_dt.hour,
                        minute=parsed_dt.minute,
                        second=parsed_dt.second,
                        microsecond=parsed_dt.microsecond,
                    )
                    # Use a 5-minute grace window to handle next-day rollover
                    if departure_time < now - timedelta(minutes=5):
                        departure_time += timedelta(days=1)
                else:
                    departure_time = parsed_dt.astimezone(now.tzinfo)
                _LOGGER.debug(
                    "Parsed departure time using parse_datetime: %s", departure_time
                )
            else:
                # Fallback for HH:MM format (assume today)
                try:
                    temp_dt = datetime.strptime(departure_time, "%H:%M")
                    departure_time = now.replace(
                        hour=temp_dt.hour,
                        minute=temp_dt.minute,
                        second=0,
                        microsecond=0,
                    )
                    # Use a 5-minute grace window to handle next-day rollover
                    if departure_time < now - timedelta(minutes=5):
                        departure_time += timedelta(days=1)
                    _LOGGER.debug(
                        "Converted departure time from fallback HH:MM: %s",
                        departure_time,
                    )
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Unable to parse departure time from string: %s",
                        departure_time,
                    )
                    return None

        if isinstance(departure_time, datetime):
            # Normalize to HA local date for comparison
            # Note: strptime outputs naive. We assume the string was in local time if no TZ was found.
            dep_date = departure_time.date()
            _LOGGER.debug("Checking departure time date: %s", dep_date)
            _LOGGER.debug("Today's date: %s", today)
            if dep_date != today:
                return departure_time.strftime("%Y-%m-%d %H:%M")
            else:
                return departure_time.strftime("%H:%M")
        else:
            _LOGGER.warning("Invalid departure time: %s", departure_time)
            return None

    @property
    def native_value(self):
        """
        Return the main state of the sensor (e.g., '10:30' or '10:30 +5').

        Calculates the state from the first entry in the coordinator's data.
        """
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
                delay_departure = self.coordinator.data[0].get("delayDeparture")
                if delay_departure is None:
                    delay_departure = self.coordinator.data[0].get("dep_delay")
                if delay_departure is None:
                    delay_departure = self.coordinator.data[0].get("delay", 0)

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
        """
        full_api_url = getattr(self.coordinator, "api_url", "dbf.finalrewind.org")
        attribution = f"Data provided by API {full_api_url}"

        # Create a deep copy or new list of dicts to avoid mutating the coordinator data
        raw_departures = self.coordinator.data or []
        next_departures = []

        for departure in raw_departures:
            # Create a shallow copy of the departure so we can modify fields for display
            dep_copy = departure.copy()

            if "scheduledTime" in dep_copy and isinstance(
                dep_copy["scheduledTime"], (int, float)
            ):
                dep_copy["scheduledTime"] = dt_util.as_local(
                    dt_util.utc_from_timestamp(int(dep_copy["scheduledTime"]))
                ).strftime("%Y-%m-%d %H:%M:%S")
            if "time" in dep_copy and isinstance(dep_copy["time"], (int, float)):
                dep_copy["time"] = dt_util.as_local(
                    dt_util.utc_from_timestamp(int(dep_copy["time"]))
                ).strftime("%Y-%m-%d %H:%M:%S")

            next_departures.append(dep_copy)

        last_updated = getattr(self.coordinator, "last_update", None)
        if last_updated:
            last_updated = last_updated.isoformat()
        else:
            last_updated = "Unknown"

        attributes = {
            "next_departures": next_departures,
            "station": self.station,
            "via_stations": self.via_stations,
            "direction": self.direction,
            "last_updated": last_updated,
            "attribution": attribution,
            "via_stations_logic": getattr(self.coordinator, "via_stations_logic", "OR"),
        }

        if self.enable_text_view:
            next_departures_text = []
            for dep in raw_departures:
                line = dep.get("line", "?")
                destination = dep.get("destination", "?")
                platform = dep.get("platform", "?")
                time = dep.get("time", "?")
                delay = dep.get("delay", 0)

                # Format time if it is an int/timestamp, otherwise use as is
                if isinstance(time, (int, float)):
                    time = dt_util.as_local(
                        dt_util.utc_from_timestamp(int(time))
                    ).strftime("%H:%M")

                delay_str = ""
                if delay:
                    try:
                        if int(delay) > 0:
                            delay_str = f" +{delay}"
                    except (ValueError, TypeError):
                        pass

                text = f"{line} -> {destination} (Pl {platform}): {time}{delay_str}"
                next_departures_text.append(text)
            attributes["next_departures_text"] = next_departures_text

        return attributes

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


class DBInfoScreenWatchdogSensor(DBInfoScreenBaseEntity, SensorEntity):
    """
    Diagnostic sensor that monitors the status of the upcoming trip.

    Looks at the previous station of the next departing train to see if it
    is on time or delayed earlier in its route.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:eye-check-outline"
    _attr_entity_registry_enabled_default = False  # Optional feature

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the watchdog sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"db_infoscreen_watchdog_{config_entry.entry_id}"
        self._attr_name = "Trip Watchdog"

    @property
    def native_value(self) -> str | None:
        """
        Return the current watchdog state.

        Shows the name and delay of the previous station for the next train.
        """
        data = self._get_watchdog_data()
        if not data:
            return "Unknown"

        station = data.get("previous_station_name")
        delay = data.get("previous_delay", 0)

        if station:
            if delay and delay > 0:
                return f"{station}: +{delay} min"
            return f"{station}: On Time"

        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about the watched trip."""
        return self._get_watchdog_data() or {}

    def _get_watchdog_data(self) -> dict[str, Any] | None:
        """Calculate watchdog data from the first departure."""
        if not self.coordinator.data:
            return None

        # Look at the first (next) departure
        next_train = self.coordinator.data[0]
        route = next_train.get("route", [])

        if not route:
            return None

        my_station_name = self.coordinator.config_entry.data.get(CONF_STATION)
        # Clean up station name (sometimes has IDs or commas)
        # Strategy:
        # 1. Try to find exact match of `self.station` (or coordinator.station) in route names.
        # 2. If found, take index - 1.

        # Let's try to find a fuzzy match or exact match
        found_index = -1
        for idx, stop in enumerate(route):
            stop_name = stop.get("name", "")
            # Simple check
            if stop_name == my_station_name or (
                my_station_name and my_station_name in stop_name
            ):
                found_index = idx
                break

        # Use first stop if not found? No, that's unreliable.
        # But for 'detailed=1', route usually contains ALL stops.

        if found_index > 0:
            prev_stop = route[found_index - 1]
            prev_name = prev_stop.get("name")
            # dep_delay is delay at departure from that stop
            # arr_delay is delay at arrival at that stop
            delay = prev_stop.get("dep_delay") or prev_stop.get("arr_delay") or 0

            return {
                "train": next_train.get("train"),
                "current_station_index": found_index,
                "previous_station_name": prev_name,
                "previous_delay": int(delay) if delay else 0,
                "updated": getattr(self.coordinator, "last_update", None),
            }

        return None


class DBInfoScreenLeaveNowSensor(DBInfoScreenBaseEntity, SensorEntity):
    """
    Utility sensor that calculates the minutes remaining until you must leave.

    Subtracts the configured 'walk time' from the next train's departure time.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "leave_now"
    _attr_entity_registry_enabled_default = False  # Disabled by default
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Leave Now Alarm"
        self._attr_unique_id = f"leave_now_{config_entry.entry_id}"
        self._attr_icon = "mdi:walk"

    @property
    def walk_time(self):
        """Get the walk time from config data or options."""
        # Options override data. 0 is a valid value, so check explicitly for None.
        opt = self.config_entry.options.get(CONF_WALK_TIME)
        if opt is not None:
            return opt
        return self.config_entry.data.get(CONF_WALK_TIME, 0)

    @property
    def native_value(self):
        """
        Return the number of minutes until the user must leave.

        Returns 'Leave now!' if the walk time has already passed.
        """
        if not self.coordinator.data or not isinstance(self.coordinator.data, list):
            return None

        # Get next departure (first in list)
        next_dep = self.coordinator.data[0]
        departure_timestamp = next_dep.get("departure_timestamp")

        if not departure_timestamp:
            return None

        now = dt_util.now().timestamp()
        minutes_until_departure = (departure_timestamp - now) / 60
        minutes_until_leave = int(minutes_until_departure - self.walk_time)

        if minutes_until_leave <= 0:
            return "Leave now!"

        return str(minutes_until_leave)

    @property
    def extra_state_attributes(self):
        if (
            not self.coordinator.data
            or not isinstance(self.coordinator.data, list)
            or len(self.coordinator.data) == 0
        ):
            return {}

        next_dep = self.coordinator.data[0]

        departure_timestamp = next_dep.get("departure_timestamp")
        if not departure_timestamp:
            return {
                "train": next_dep.get("train"),
                "destination": next_dep.get("destination"),
                "departure_time": next_dep.get("departure_current"),
                "walk_time": self.walk_time,
                "next_departures_count": len(self.coordinator.data),
                "status": None,
            }

        minutes_until_departure = (departure_timestamp - dt_util.now().timestamp()) / 60
        minutes_until_leave = int(minutes_until_departure - self.walk_time)
        status = "Leave now!" if minutes_until_leave <= 0 else "On time"

        return {
            "train": next_dep.get("train"),
            "destination": next_dep.get("destination"),
            "departure_time": next_dep.get("departure_current"),
            "walk_time": self.walk_time,
            "next_departures_count": len(self.coordinator.data),
            "status": status,
        }


class DBInfoScreenPunctualitySensor(DBInfoScreenBaseEntity, SensorEntity):
    """
    Statistical sensor for station punctuality.

    Displays the percentage of trains that were on time (delay <= 5 min)
    over the last 24 hours.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "punctuality"
    _attr_entity_registry_enabled_default = False  # Disabled by default
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator, config_entry)
        self._attr_name = "Station Punctuality"
        self._attr_unique_id = f"punctuality_{config_entry.entry_id}"
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self):
        """Return the calculated punctuality percentage."""
        stats = self._get_stats()
        return stats.get("punctuality_percent")

    @property
    def extra_state_attributes(self):
        return self._get_stats()

    def _get_stats(self):
        """Calculate statistics from history."""
        history = getattr(self.coordinator, "departure_history", {})
        if not history:
            return {
                "punctuality_percent": None,
                "total_trains": 0,
                "delayed_trains": 0,
                "cancelled_trains": 0,
                "average_delay": 0,
            }

        total = len(history)
        delayed = sum(
            1
            for d in history.values()
            if d.get("delay", 0) > 5 and not d.get("cancelled", False)
        )
        cancelled = sum(1 for d in history.values() if d.get("cancelled", False))
        on_time = total - delayed - cancelled

        punctuality = round((on_time / total) * 100, 1) if total > 0 else 100

        total_delay = sum(
            d.get("delay", 0) for d in history.values() if not d.get("cancelled", False)
        )
        avg_delay = (
            round(total_delay / (total - cancelled), 1)
            if (total - cancelled) > 0
            else 0
        )

        return {
            "punctuality_percent": punctuality,
            "total_trains": total,
            "delayed_trains": delayed,
            "cancelled_trains": cancelled,
            "average_delay": avg_delay,
        }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    Set up a DBInfoSensor entity for the given config entry.
    """
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    station = config_entry.data.get("station")
    via_stations = config_entry.data.get("via_stations", [])
    direction = config_entry.data.get("direction", "")
    platforms = config_entry.data.get("platforms", "")
    enable_text_view = config_entry.options.get(CONF_ENABLE_TEXT_VIEW, False)

    _LOGGER.debug("Setting up DBInfoScreen sensors for station: %s", station)

    entities = [
        DBInfoSensor(
            coordinator,
            config_entry,
            station,
            via_stations,
            direction,
            platforms,
            enable_text_view,
        ),
        DBInfoScreenWatchdogSensor(coordinator, config_entry),
        DBInfoScreenLeaveNowSensor(coordinator, config_entry),
        DBInfoScreenPunctualitySensor(coordinator, config_entry),
    ]

    async_add_entities(entities)

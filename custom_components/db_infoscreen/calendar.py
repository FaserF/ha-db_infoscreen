"""Calendar platform for DB Infoscreen integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, cast

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import DBInfoScreenBaseEntity
from .utils import parse_datetime_flexible

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DB Infoscreen calendar platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            DBInfoScreenCalendar(coordinator, config_entry),
        ]
    )


class DBInfoScreenCalendar(DBInfoScreenBaseEntity, CalendarEntity):
    """Calendar entity that shows train departures as events."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False  # Disabled by default

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator, config_entry)

        self._attr_unique_id = f"db_infoscreen_calendar_{config_entry.entry_id}"
        self._attr_translation_key = "calendar_departures"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        events = self._get_events_from_departures()
        # Filter for future events only (where end time is in the future)
        future_events = [e for e in events if e.end > now]
        if future_events:
            return future_events[0]
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        all_events = self._get_events_from_departures()

        # Filter events within the date range
        filtered_events = []
        for event in all_events:
            if event.end > start_date and event.start < end_date:
                filtered_events.append(event)

        return filtered_events

    def _get_events_from_departures(self) -> list[CalendarEvent]:
        """Convert departure data to calendar events."""
        events = []
        departures: list[dict[str, Any]] = cast(
            list[dict[str, Any]], self.coordinator.data or []
        )
        now = dt_util.now()

        # Load options from coordinator
        walk_time = getattr(self.coordinator, "walk_time", 0)
        event_duration = getattr(self.coordinator, "calendar_event_duration", 5)
        only_favorites = getattr(self.coordinator, "calendar_only_favorites", False)
        only_delayed = getattr(self.coordinator, "calendar_only_delayed", False)

        for departure in departures:
            try:
                # Extract departure time
                departure_time = self._parse_departure_time(departure, now)
                if not departure_time:
                    continue

                # Extract other fields
                line = departure.get("line", departure.get("train", "Unknown"))
                destination = departure.get("destination", "Unknown")
                platform = departure.get(
                    "platform", departure.get("scheduledPlatform", "?")
                )
                delay = departure.get("delay", departure.get("delayDeparture", 0))
                cancelled = departure.get("is_cancelled", False)

                # Parse delay
                try:
                    delay_int = (
                        int(delay)
                        if delay is not None
                        and (str(delay).isdigit() or isinstance(delay, (int, float)))
                        else 0
                    )
                except (ValueError, TypeError):
                    delay_int = 0

                # 1. Filter: Only Delayed Trains
                if only_delayed and delay_int <= 0:
                    continue

                # 2. Filter: Only Favorite Trains
                if only_favorites:
                    train_name = departure.get("train", "")
                    line_name = departure.get("line", "")
                    train_num = str(departure.get("trainNumber", ""))
                    trip_id = str(departure.get("id", ""))
                    is_fav = False
                    for fav in getattr(self.coordinator, "favorite_trains", []):
                        if (
                            (train_name and fav.lower() in train_name.lower())
                            or (line_name and fav.lower() in line_name.lower())
                            or (train_num and fav == train_num)
                            or (trip_id and fav == trip_id)
                        ):
                            is_fav = True
                            break
                    if not is_fav:
                        continue

                # Account for delay in calendar event times
                actual_departure_time = departure_time + timedelta(minutes=delay_int)

                # Apply walk time buffer before start time
                actual_start_time = actual_departure_time - timedelta(minutes=walk_time)
                end_time = actual_departure_time + timedelta(minutes=event_duration)

                delay_str = f" (+{delay_int}min)" if delay_int > 0 else ""
                cancelled_str = " ⚠️ CANCELLED" if cancelled else ""
                summary = f"{line} → {destination}{delay_str}{cancelled_str}"

                # Build description with details
                description_parts = [
                    f"Line: {line}",
                    f"Destination: {destination}",
                    f"Platform: {platform}",
                    f"Station: {self.station}",
                    f"Scheduled Time: {departure_time.strftime('%H:%M')}",
                ]
                if walk_time > 0:
                    description_parts.append(f"Walk Time: {walk_time} minutes")
                    description_parts.append(
                        f"Start walking at: {actual_start_time.strftime('%H:%M')}"
                    )
                if delay_int > 0:
                    description_parts.append(f"Delay: {delay_int} minutes")
                    description_parts.append(
                        f"Estimated Departure: {actual_departure_time.strftime('%H:%M')}"
                    )
                if cancelled:
                    description_parts.append("⚠️ This train has been CANCELLED")

                # Add route info if available
                route = departure.get("via", departure.get("route", []))
                if route:
                    if isinstance(route, list):
                        route_str = " → ".join([str(s) for s in route[:5]])
                        if len(route) > 5:
                            route_str += f" ... (+{len(route) - 5} more)"
                    else:
                        route_str = str(route)
                    description_parts.append(f"Via: {route_str}")

                # 3. Add deep link
                fetch_url = getattr(self.coordinator, "fetch_url", None)
                if fetch_url:
                    description_parts.append(f"Connection Details: {fetch_url}")

                description = "\n".join(description_parts)

                event = CalendarEvent(
                    start=actual_start_time,
                    end=end_time,
                    summary=summary,
                    description=description,
                    location=f"Platform {platform}, {self.station}",
                )
                events.append(event)

            except Exception as e:
                _LOGGER.debug("Error parsing departure for calendar: %s", e)
                continue

        # Sort by start time
        events.sort(key=lambda e: e.start)
        return events

    def _parse_departure_time(
        self, departure: dict[str, Any], now: datetime
    ) -> datetime | None:
        """Parse departure time using centralized logic."""
        departure_time_str = (
            departure.get("scheduledDeparture")
            or departure.get("sched_dep")
            or departure.get("scheduledArrival")
            or departure.get("sched_arr")
            or departure.get("scheduledTime")
            or departure.get("dep")
            or departure.get("datetime")
        )
        return parse_datetime_flexible(departure_time_str, now)

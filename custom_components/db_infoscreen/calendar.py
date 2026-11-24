"""Calendar platform for DB Infoscreen integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import DBInfoScreenBaseEntity
from .utils import parse_datetime_flexible

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ParsedCalendarEntry:
    """Lightweight pre-parsed departure entry before CalendarEvent validation."""

    start: datetime
    end: datetime
    departure_time: datetime
    delay_int: int
    line: Any
    destination: Any
    platform: Any
    cancelled: bool
    route: Any


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
        self._cached_key: tuple[Any, ...] | None = None
        self._cached_entries: list[_ParsedCalendarEntry] = []
        self._cached_events: dict[int, CalendarEvent] = {}
        self._cached_fetch_url: str | None = None
        self._cached_walk_time: int = 0

    def _invalidate_cache(self) -> None:
        """Clear cached departure entries and built CalendarEvent objects."""
        self._cached_key = None
        self._cached_entries = []
        self._cached_events.clear()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Invalidate cached calendar entries when coordinator updates."""
        self._invalidate_cache()
        super()._handle_coordinator_update()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        entries = self._get_sorted_entries(now)
        for idx, entry in enumerate(entries):
            if entry.end > now:
                return self._get_or_build_event(idx, entry)
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        entries = self._get_sorted_entries(dt_util.now())
        return [
            self._get_or_build_event(idx, entry)
            for idx, entry in enumerate(entries)
            if entry.end > start_date and entry.start < end_date
        ]

    def _get_events_from_departures(self) -> list[CalendarEvent]:
        """Convert departure data to calendar events."""
        entries = self._get_sorted_entries(dt_util.now())
        return [
            self._get_or_build_event(idx, entry) for idx, entry in enumerate(entries)
        ]

    def _get_or_build_event(
        self, idx: int, entry: _ParsedCalendarEntry
    ) -> CalendarEvent:
        """Build and cache a validated CalendarEvent only when needed."""
        cached = self._cached_events.get(idx)
        if cached is not None:
            return cached

        delay_str = f" (+{entry.delay_int}min)" if entry.delay_int > 0 else ""
        cancelled_str = " ⚠️ CANCELLED" if entry.cancelled else ""
        summary = f"{entry.line} → {entry.destination}{delay_str}{cancelled_str}"

        description_parts = [
            f"Line: {entry.line}",
            f"Destination: {entry.destination}",
            f"Platform: {entry.platform}",
            f"Station: {self.station}",
            f"Scheduled Time: {entry.departure_time.strftime('%H:%M')}",
        ]
        if self._cached_walk_time > 0:
            description_parts.append(f"Walk Time: {self._cached_walk_time} minutes")
            description_parts.append(
                f"Start walking at: {entry.start.strftime('%H:%M')}"
            )
        if entry.delay_int > 0:
            description_parts.append(f"Delay: {entry.delay_int} minutes")
            actual_departure_time = entry.departure_time + timedelta(
                minutes=entry.delay_int
            )
            description_parts.append(
                f"Estimated Departure: {actual_departure_time.strftime('%H:%M')}"
            )
        if entry.cancelled:
            description_parts.append("⚠️ This train has been CANCELLED")

        if entry.route:
            if isinstance(entry.route, list):
                route_str = " → ".join(str(s) for s in entry.route[:5])
                if len(entry.route) > 5:
                    route_str += f" ... (+{len(entry.route) - 5} more)"
            else:
                route_str = str(entry.route)
            description_parts.append(f"Via: {route_str}")

        if self._cached_fetch_url:
            description_parts.append(f"Connection Details: {self._cached_fetch_url}")

        location = (
            f"Platform {entry.platform}, {self.station}"
            if entry.platform and entry.platform != "?"
            else self.station
        )
        built = CalendarEvent(
            start=entry.start,
            end=entry.end,
            summary=summary,
            description="\n".join(description_parts),
            location=location,
        )
        self._cached_events[idx] = built
        return built

    def _get_sorted_entries(self, now: datetime) -> list[_ParsedCalendarEntry]:
        """Parse and cache lightweight departure entries for current coordinator data."""
        departures: list[dict[str, Any]] = cast(
            list[dict[str, Any]], self.coordinator.data or []
        )
        if not departures:
            self._invalidate_cache()
            return []

        walk_time = getattr(self.coordinator, "walk_time", 0)
        event_duration = getattr(self.coordinator, "calendar_event_duration", 5)
        only_favorites = bool(
            getattr(self.coordinator, "calendar_only_favorites", False)
        )
        only_delayed = bool(getattr(self.coordinator, "calendar_only_delayed", False))
        favorite_trains_raw = getattr(self.coordinator, "favorite_trains", None) or ()
        favorite_trains = tuple(str(f).lower() for f in favorite_trains_raw)
        favorite_trains_exact = tuple(str(f) for f in favorite_trains_raw)
        fetch_url = getattr(self.coordinator, "fetch_url", None)
        last_update = getattr(self.coordinator, "last_update", None)

        cache_key = (
            id(departures),
            len(departures),
            last_update,
            walk_time,
            event_duration,
            only_favorites,
            only_delayed,
            favorite_trains_exact,
            fetch_url,
            now.date(),
            now.tzinfo,
        )
        if cache_key == self._cached_key:
            return self._cached_entries

        walk_delta = timedelta(minutes=walk_time)
        duration_delta = timedelta(minutes=event_duration)
        entries: list[_ParsedCalendarEntry] = []

        for departure in departures:
            try:
                departure_time = self._parse_departure_time(departure, now)
                if not departure_time:
                    continue

                line = departure.get("line", departure.get("train", "Unknown"))
                destination = departure.get("destination", "Unknown")
                platform = (
                    departure.get("platform")
                    or departure.get("scheduledPlatform")
                    or "?"
                )
                delay = departure.get("delay", departure.get("delayDeparture", 0))
                cancelled = bool(departure.get("is_cancelled", False))

                try:
                    delay_int = (
                        int(delay)
                        if delay is not None
                        and (str(delay).isdigit() or isinstance(delay, (int, float)))
                        else 0
                    )
                except ValueError, TypeError:
                    delay_int = 0

                if only_delayed and delay_int <= 0:
                    continue

                if only_favorites:
                    train_name_lower = str(departure.get("train", "")).lower()
                    line_name_lower = str(departure.get("line", "")).lower()
                    train_num = str(departure.get("trainNumber", ""))
                    trip_id = str(departure.get("id", ""))
                    is_fav = False
                    for fav_lower, fav_exact in zip(
                        favorite_trains, favorite_trains_exact, strict=False
                    ):
                        if (
                            (train_name_lower and fav_lower in train_name_lower)
                            or (line_name_lower and fav_lower in line_name_lower)
                            or (train_num and fav_exact == train_num)
                            or (trip_id and fav_exact == trip_id)
                        ):
                            is_fav = True
                            break
                    if not is_fav:
                        continue

                actual_departure_time = departure_time + timedelta(minutes=delay_int)
                entries.append(
                    _ParsedCalendarEntry(
                        start=actual_departure_time - walk_delta,
                        end=actual_departure_time + duration_delta,
                        departure_time=departure_time,
                        delay_int=delay_int,
                        line=line,
                        destination=destination,
                        platform=platform,
                        cancelled=cancelled,
                        route=departure.get("via", departure.get("route", [])),
                    )
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Error parsing departure for calendar: %s", e)
                continue

        entries.sort(key=lambda e: e.start)
        self._cached_key = cache_key
        self._cached_entries = entries
        self._cached_events.clear()
        self._cached_fetch_url = fetch_url
        self._cached_walk_time = walk_time
        return entries

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

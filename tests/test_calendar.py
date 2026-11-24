"""Tests for calendar platform in DB Infoscreen integration."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.db_infoscreen.calendar import DBInfoScreenCalendar


@pytest.mark.asyncio
async def test_calendar_event_generation(hass: HomeAssistant) -> None:
    """Test calendar event generation with duration, walk time, filtering and links."""
    mock_coordinator = MagicMock()
    mock_coordinator.station = "München Hbf"
    mock_coordinator.fetch_url = "https://example.com/api"
    mock_coordinator.favorite_trains = ["S 3"]

    # Configure options on coordinator
    mock_coordinator.walk_time = 10
    mock_coordinator.calendar_event_duration = 15
    mock_coordinator.calendar_only_favorites = False
    mock_coordinator.calendar_only_delayed = False

    # Mock departures data
    now = datetime(2026, 6, 21, 12, 0, 0, tzinfo=UTC)
    mock_coordinator.data = [
        {
            "line": "S 3",
            "destination": "Holzkirchen",
            "scheduledDeparture": "2026-06-21T12:15:00Z",
            "delay": 5,
            "platform": "1",
            "is_cancelled": False,
        },
        {
            "line": "S 8",
            "destination": "Herrsching",
            "scheduledDeparture": "2026-06-21T12:20:00Z",
            "delay": 0,
            "platform": "2",
            "is_cancelled": False,
        },
    ]

    entity = DBInfoScreenCalendar(mock_coordinator, MagicMock())

    # Generate events
    with patch("homeassistant.util.dt.now", return_value=now):
        events = entity._get_events_from_departures()

    assert len(events) == 2

    # S 3 actual departure: 12:15 + 5 min delay = 12:20
    # Walk time buffer: 10 minutes -> Event starts at 12:10
    # Event duration: 15 minutes -> Event ends at 12:20 + 15 min = 12:35
    event1 = events[0]
    assert event1.summary == "S 3 → Holzkirchen (+5min)"
    assert event1.start == datetime(2026, 6, 21, 12, 10, 0, tzinfo=UTC)
    assert event1.end == datetime(2026, 6, 21, 12, 35, 0, tzinfo=UTC)
    assert "Connection Details: https://example.com/api" in event1.description
    assert "Walk Time: 10 minutes" in event1.description

    # S 8 actual departure: 12:20
    # Walk time buffer: 10 minutes -> Event starts at 12:10
    # Event duration: 15 minutes -> Event ends at 12:20 + 15 min = 12:35
    event2 = events[1]
    assert event2.summary == "S 8 → Herrsching"
    assert event2.start == datetime(2026, 6, 21, 12, 10, 0, tzinfo=UTC)
    assert event2.end == datetime(2026, 6, 21, 12, 35, 0, tzinfo=UTC)

    # Test calendar filter: Only delayed
    mock_coordinator.calendar_only_delayed = True
    with patch("homeassistant.util.dt.now", return_value=now):
        delayed_events = entity._get_events_from_departures()
    assert len(delayed_events) == 1
    assert delayed_events[0].summary == "S 3 → Holzkirchen (+5min)"

    # Test calendar filter: Only favorites
    mock_coordinator.calendar_only_delayed = False
    mock_coordinator.calendar_only_favorites = True
    with patch("homeassistant.util.dt.now", return_value=now):
        fav_events = entity._get_events_from_departures()
    assert len(fav_events) == 1
    assert fav_events[0].summary == "S 3 → Holzkirchen (+5min)"


@pytest.mark.asyncio
async def test_calendar_event_caching_and_invalidation(hass: HomeAssistant) -> None:
    """Test calendar caches parsed departures and builds only the next CalendarEvent on state reads."""
    mock_coordinator = MagicMock()
    mock_coordinator.station = "Zorneding"
    mock_coordinator.fetch_url = "https://example.com/Zorneding.json"
    mock_coordinator.favorite_trains = []
    mock_coordinator.walk_time = 0
    mock_coordinator.calendar_event_duration = 5
    mock_coordinator.calendar_only_favorites = False
    mock_coordinator.calendar_only_delayed = False
    mock_coordinator.last_update = datetime(2026, 6, 21, 12, 0, 0, tzinfo=UTC)
    mock_coordinator.data = [
        {
            "line": f"S {i}",
            "destination": "München",
            "scheduledDeparture": f"{12 + (i // 60):02d}:{i % 60:02d}",
            "delay": 0,
            "platform": "1",
            "is_cancelled": False,
        }
        for i in range(1, 200)
    ]

    entity = DBInfoScreenCalendar(mock_coordinator, MagicMock())
    now = datetime(2026, 6, 21, 12, 0, 0, tzinfo=UTC)

    with patch("homeassistant.util.dt.now", return_value=now):
        with patch.object(
            entity, "_parse_departure_time", wraps=entity._parse_departure_time
        ) as mock_parse:
            # Simulates CalendarEntity._async_write_ha_state calling state, state_attributes, and event
            state_val = entity.state
            attrs_val = entity.state_attributes
            next_event = entity.event
            assert state_val == "off"
            assert attrs_val is not None
            assert next_event is not None
            assert next_event.summary == "S 1 → München"
            # Parsed once across 3 property reads, and built only 1 CalendarEvent
            assert mock_parse.call_count == len(mock_coordinator.data)
            assert len(entity._cached_events) == 1

            # Subsequent async_get_events reuses parsed entries without re-parsing
            window_events = await entity.async_get_events(
                hass,
                datetime(2026, 6, 21, 12, 10, 0, tzinfo=UTC),
                datetime(2026, 6, 21, 12, 15, 0, tzinfo=UTC),
            )
            assert mock_parse.call_count == len(mock_coordinator.data)
            assert len(window_events) > 0

        # Coordinator update invalidates the cache
        mock_coordinator.last_update = datetime(2026, 6, 21, 12, 0, 30, tzinfo=UTC)
        mock_coordinator.data = [
            {
                "line": "S 6",
                "destination": "Tutzing",
                "scheduledDeparture": "12:05",
                "delay": 2,
                "platform": "2",
                "is_cancelled": False,
            }
        ]
        entity._invalidate_cache()
        assert entity.event is not None
        assert entity.event.summary == "S 6 → Tutzing (+2min)"

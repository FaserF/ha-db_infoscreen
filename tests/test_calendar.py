"""Tests for calendar platform in DB Infoscreen integration."""

from datetime import datetime, timezone
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
    now = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
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
    assert event1.start == datetime(2026, 6, 21, 12, 10, 0, tzinfo=timezone.utc)
    assert event1.end == datetime(2026, 6, 21, 12, 35, 0, tzinfo=timezone.utc)
    assert "Connection Details: https://example.com/api" in event1.description
    assert "Walk Time: 10 minutes" in event1.description

    # S 8 actual departure: 12:20
    # Walk time buffer: 10 minutes -> Event starts at 12:10
    # Event duration: 15 minutes -> Event ends at 12:20 + 15 min = 12:35
    event2 = events[1]
    assert event2.summary == "S 8 → Herrsching"
    assert event2.start == datetime(2026, 6, 21, 12, 10, 0, tzinfo=timezone.utc)
    assert event2.end == datetime(2026, 6, 21, 12, 35, 0, tzinfo=timezone.utc)

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

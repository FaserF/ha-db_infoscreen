from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator


@pytest.fixture
def mock_coordinator(hass):
    config_entry = MagicMock()
    config_entry.data = {"station": "München Hbf"}
    config_entry.options = {}
    coordinator = DBInfoScreenCoordinator(hass, config_entry)
    return coordinator


@pytest.mark.asyncio
async def test_watch_train_notification_trigger(hass, mock_coordinator):
    """Test that a notification is triggered for a watched train."""

    # 1. Setup Watchlist
    mock_coordinator.watched_trips["ICE 123"] = {
        "notify_service": "notify.mobile_app",
        "delay_threshold": 5,
        "notify_on_platform_change": True,
        "notify_on_cancellation": True,
        "last_notified_delay": -1,
        "last_notified_platform": None,
        "last_notified_cancellation": False,
    }

    # 2. Mock Departures with delay
    departures = [
        {
            "train": "ICE 123",
            "destination": "Berlin",
            "delayDeparture": 10,
            "platform": "1",
            "isCancelled": False,
        }
    ]

    # 3. Trigger check
    with patch.object(
        hass.services, "async_call", new_callable=AsyncMock
    ) as mock_service:
        await mock_coordinator._check_watched_trips(departures)

        # Verify notification sent
        mock_service.assert_called_once()
        args = mock_service.call_args[0]
        assert args[0] == "notify"
        assert args[1] == "mobile_app"
        assert "Delay is now 10 min" in args[2]["message"]


@pytest.mark.asyncio
async def test_watch_train_no_double_notification(hass, mock_coordinator):
    """Test that we don't notify multiple times for the same delay."""

    mock_coordinator.watched_trips["ICE 123"] = {
        "notify_service": "notify.mobile_app",
        "delay_threshold": 5,
        "notify_on_platform_change": True,
        "notify_on_cancellation": True,
        "last_notified_delay": 10,  # Already notified
        "last_notified_platform": "1",
        "last_notified_cancellation": False,
    }

    departures = [
        {
            "train": "ICE 123",
            "destination": "Berlin",
            "delayDeparture": 10,
            "platform": "1",
            "isCancelled": False,
        }
    ]

    with patch.object(
        hass.services, "async_call", new_callable=AsyncMock
    ) as mock_service:
        await mock_coordinator._check_watched_trips(departures)
        mock_service.assert_not_called()


@pytest.mark.asyncio
async def test_watch_train_cancellation(hass, mock_coordinator):
    """Test notification on cancellation."""

    mock_coordinator.watched_trips["ICE 123"] = {
        "notify_service": "notify.mobile_app",
        "delay_threshold": 5,
        "notify_on_platform_change": True,
        "notify_on_cancellation": True,
        "last_notified_delay": -1,
        "last_notified_platform": None,
        "last_notified_cancellation": False,
    }

    departures = [
        {
            "train": "ICE 123",
            "destination": "Berlin",
            "delayDeparture": 0,
            "platform": "1",
            "is_cancelled": True,
        }
    ]

    with patch.object(
        hass.services, "async_call", new_callable=AsyncMock
    ) as mock_service:
        await mock_coordinator._check_watched_trips(departures)
        mock_service.assert_called_once()
        assert "CANCELLED" in mock_service.call_args[0][2]["message"]

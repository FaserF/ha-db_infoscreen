from unittest.mock import MagicMock
import pytest
from custom_components.db_infoscreen.sensor import DBInfoScreenPunctualitySensor
from homeassistant.util import dt as dt_util


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.departure_history = {}
    coord.config_entry = MagicMock()
    coord.config_entry.data = {}
    coord.config_entry.options = {}
    return coord


@pytest.mark.asyncio
async def test_punctuality_sensor_calculation(hass, mock_coordinator):
    """Test the statistics calculation logic."""
    now = dt_util.now()

    # 1. Setup history: 1 on-time, 1 delayed (10m), 1 cancelled
    mock_coordinator.departure_history = {
        "trip1": {"train": "ICE 1", "delay": 0, "cancelled": False, "timestamp": now},
        "trip2": {"train": "ICE 2", "delay": 10, "cancelled": False, "timestamp": now},
        "trip3": {"train": "ICE 3", "delay": 0, "cancelled": True, "timestamp": now},
    }

    sensor = DBInfoScreenPunctualitySensor(
        mock_coordinator, mock_coordinator.config_entry
    )

    stats = sensor._get_stats()

    # total=3, delayed=1, cancelled=1, on_time=1
    # punctuality = (1 / 3) * 100 = 33.3%
    assert stats["total_trains"] == 3
    assert stats["delayed_trains"] == 1
    assert stats["cancelled_trains"] == 1
    assert stats["punctuality_percent"] == 33.3

    # avg_delay = (0 + 10) / (3-1) = 5.0
    assert stats["average_delay"] == 5.0


@pytest.mark.asyncio
async def test_punctuality_sensor_empty(hass, mock_coordinator):
    """Test statistics when history is empty."""
    sensor = DBInfoScreenPunctualitySensor(
        mock_coordinator, mock_coordinator.config_entry
    )
    stats = sensor._get_stats()

    assert stats["total_trains"] == 0
    assert stats["punctuality_percent"] is None

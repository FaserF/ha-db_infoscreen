from unittest.mock import MagicMock, patch
import pytest
from homeassistant.util import dt as dt_util
from custom_components.db_infoscreen.sensor import DBInfoScreenLeaveNowSensor


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"station": "Karlsruhe Hbf", "walk_time": 5}
    entry.options = {}
    return entry


@pytest.mark.asyncio
async def test_leave_now_numeric_value(hass, mock_config_entry):
    """Test that the leave now sensor returns a numeric value (0) instead of a string."""
    coordinator = MagicMock()
    now_dt = dt_util.now()
    now = now_dt.timestamp()

    # Departure in 4 minutes, walk time 5 minutes -> minutes_until_leave = -1
    coordinator.data = [
        {
            "train": "S2",
            "departure_timestamp": now + 4 * 60,
            "departure_current": "10:04",
        }
    ]

    sensor = DBInfoScreenLeaveNowSensor(coordinator, mock_config_entry)

    # native_value should be 0 (numeric)
    with patch("homeassistant.util.dt.now", return_value=now_dt):
        val = sensor.native_value
        assert val == 0
        assert isinstance(val, int)

    # Attributes should still have "Leave now!"
    attrs = sensor.extra_state_attributes
    assert attrs["status"] == "Leave now!"
    assert attrs["walk_time"] == 5


@pytest.mark.asyncio
async def test_leave_later_numeric_value(hass, mock_config_entry):
    """Test that the leave now sensor returns a numeric value when not yet time to leave."""
    coordinator = MagicMock()
    now_dt = dt_util.now()
    now = now_dt.timestamp()

    # Departure in 10 minutes, walk time 5 minutes -> minutes_until_leave = 5
    coordinator.data = [
        {
            "train": "S2",
            "departure_timestamp": now + 10 * 60,
            "departure_current": "10:10",
        }
    ]

    sensor = DBInfoScreenLeaveNowSensor(coordinator, mock_config_entry)

    # native_value should be 5 (numeric)
    with patch("homeassistant.util.dt.now", return_value=now_dt):
        val = sensor.native_value
        assert val == 5
        assert isinstance(val, int)

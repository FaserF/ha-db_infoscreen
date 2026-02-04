from unittest.mock import MagicMock, patch
import pytest
from custom_components.db_infoscreen.sensor import DBInfoScreenLeaveNowSensor
from custom_components.db_infoscreen.const import CONF_WALK_TIME
from homeassistant.util import dt as dt_util
from datetime import timedelta


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.data = []
    # Mock config_entry
    coord.config_entry = MagicMock()
    coord.config_entry.data = {}
    coord.config_entry.options = {}
    return coord


@pytest.mark.asyncio
async def test_leave_now_sensor_logic(hass, mock_coordinator):
    """Test the calculation logic of the Leave Now sensor."""
    # 1. Setup sensor with 10 min walk time
    mock_coordinator.config_entry.options[CONF_WALK_TIME] = 10
    sensor = DBInfoScreenLeaveNowSensor(mock_coordinator, mock_coordinator.config_entry)

    # 2. Mock departure in 25 minutes
    now = dt_util.now()
    departure_ts = (now + timedelta(minutes=25)).timestamp()
    mock_coordinator.data = [
        {
            "departure_timestamp": departure_ts,
            "train": "ICE 1",
            "destination": "Berlin",
            "departure_current": "10:25",
        }
    ]

    # 3. Verify: 25 - 10 = 15 minutes left
    # Note: Use mock for now to be precise
    with patch("homeassistant.util.dt.now", return_value=now):
        assert sensor.native_value == "15"


@pytest.mark.asyncio
async def test_leave_now_immediate(hass, mock_coordinator):
    """Test "Leave now!" state when time is up."""
    mock_coordinator.config_entry.options[CONF_WALK_TIME] = 10
    sensor = DBInfoScreenLeaveNowSensor(mock_coordinator, mock_coordinator.config_entry)

    # Departure in 5 minutes, but walk is 10 minutes -> Too late / Leave NOW
    now = dt_util.now()
    departure_ts = (now + timedelta(minutes=5)).timestamp()
    mock_coordinator.data = [{"departure_timestamp": departure_ts}]

    with patch("homeassistant.util.dt.now", return_value=now):
        assert sensor.native_value == "Leave now!"


@pytest.mark.asyncio
async def test_leave_now_no_data(hass, mock_coordinator):
    """Test sensor with no data."""
    sensor = DBInfoScreenLeaveNowSensor(mock_coordinator, mock_coordinator.config_entry)
    mock_coordinator.data = []
    assert sensor.native_value is None

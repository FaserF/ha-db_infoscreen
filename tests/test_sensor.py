from unittest.mock import MagicMock, patch
from datetime import timedelta
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_ENABLE_TEXT_VIEW,
)


@pytest.fixture
def mock_coordinator(hass):
    """Create a mock coordinator stub."""

    class CoordinatorStub:
        def __init__(self, hass):
            self.hass = hass
            self.data = []
            self.last_update_success = True
            self.logger = MagicMock()
            self.name = "test_coordinator"

        def async_add_listener(self, *args):
            pass

        def async_remove_listener(self, *args):
            pass

    return CoordinatorStub(hass)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "123"
    entry.data = {
        CONF_STATION: "München Hbf",
        "via_stations": [],
        "direction": "",
        "platforms": "",
    }
    entry.options = {
        CONF_ENABLE_TEXT_VIEW: False,
    }
    return entry


@pytest.fixture
def fixed_now():
    """Return a fixed time for testing."""
    return dt_util.parse_datetime("2026-01-29T08:00:00+01:00")


async def test_sensor_state_logic(
    hass: HomeAssistant, mock_coordinator, mock_config_entry, fixed_now
):
    """Test the sensor state and attributes logic."""
    from custom_components.db_infoscreen.sensor import DBInfoSensor

    sensor = DBInfoSensor(
        mock_coordinator,
        mock_config_entry,
        "München Hbf",
        [],
        "",
        "",
        False,
    )
    sensor.hass = hass
    sensor.entity_id = "sensor.test"
    sensor.platform = MagicMock()

    with patch("homeassistant.util.dt.now", return_value=fixed_now):
        # Test initial state (No Data)
        assert sensor.native_value == "No Data"

        # Test with data
        dep_time = fixed_now + timedelta(minutes=10)

        mock_coordinator.data = [
            {
                "scheduledDeparture": dep_time.strftime("%Y-%m-%dT%H:%M"),
                "delayDeparture": 5,
                "destination": "Hamburg",
                "train": "ICE 1",
                "platform": "1",
            }
        ]

        # State should be time + delay
        assert sensor.native_value == f"{dep_time.strftime('%H:%M')} +5"

    # Test attributes
    attrs = sensor.extra_state_attributes
    assert len(attrs["next_departures"]) == 1
    assert attrs["next_departures"][0]["destination"] == "Hamburg"


async def test_sensor_text_view(
    hass: HomeAssistant, mock_coordinator, mock_config_entry, fixed_now
):
    """Test text view generation."""
    from custom_components.db_infoscreen.sensor import DBInfoSensor

    sensor = DBInfoSensor(
        mock_coordinator,
        mock_config_entry,
        "München Hbf",
        [],
        "",
        "",
        True,  # Enable text view
    )
    sensor.hass = hass
    sensor.entity_id = "sensor.test"
    sensor.platform = MagicMock()

    with patch("homeassistant.util.dt.now", return_value=fixed_now):
        mock_coordinator.data = [
            {
                "line": "ICE 1",
                "destination": "Hamburg",
                "platform": "1",
                "time": fixed_now.timestamp(),  # Using timestamp
                "delay": 0,
                "scheduledDeparture": fixed_now.strftime("%Y-%m-%dT%H:%M"),
            }
        ]
        sensor._handle_coordinator_update()
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "next_departures_text" in attrs
        text_lines = attrs["next_departures_text"]
        assert len(text_lines) == 1
        # Check format: ICE 1 -> Hamburg (Pl 1): HH:MM
        assert "ICE 1 -> Hamburg (Pl 1):" in text_lines[0]

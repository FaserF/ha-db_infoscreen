"""Tests for the DB Infoscreen sensor."""

from unittest.mock import AsyncMock, MagicMock, patch
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
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = []
    return coordinator


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


async def test_sensor_setup(hass: HomeAssistant):
    """Test setting up the sensor."""
    with patch(
        "custom_components.db_infoscreen.DBInfoScreenCoordinator"
    ) as mock_coordinator_cls:
        mock_coordinator = mock_coordinator_cls.return_value
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = []

        entry = MagicMock()
        entry.entry_id = "123"
        entry.data = {
            CONF_STATION: "München Hbf",
        }
        entry.options = {}
        entry.add_update_listener = MagicMock()

        hass.config_entries.async_forward_entry_setups = AsyncMock()

        # We can't easily test the full setup flow without installing the integration
        # But we can test the sensor logic by instantiating it directly if we want
        # or by simulating the component setup.
        pass


async def test_sensor_state_logic(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
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

    # Test initial state (No Data)
    assert sensor.native_value == "No Data"

    # Test with data
    now = dt_util.now()
    dep_time = now + timedelta(minutes=10)

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
    hass: HomeAssistant, mock_coordinator, mock_config_entry
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

    now = dt_util.now()
    mock_coordinator.data = [
        {
            "line": "ICE 1",
            "destination": "Hamburg",
            "platform": "1",
            "time": now.timestamp(),  # Using timestamp
            "delay": 0,
        }
    ]

    attrs = sensor.extra_state_attributes
    assert "next_departures_text" in attrs
    text_lines = attrs["next_departures_text"]
    assert len(text_lines) == 1
    # Check format: ICE 1 -> Hamburg (Pl 1): HH:MM
    assert "ICE 1 -> Hamburg (Pl 1):" in text_lines[0]

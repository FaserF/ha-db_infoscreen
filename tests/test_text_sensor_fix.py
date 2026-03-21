from unittest.mock import MagicMock
import pytest
from homeassistant.util import dt as dt_util
from custom_components.db_infoscreen.sensor import DBInfoSensor


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"station": "Karlsruhe Hbf"}
    entry.options = {}
    return entry


@pytest.mark.asyncio
async def test_next_departures_text_diverse_keys(hass, mock_config_entry):
    """Test that next_departures_text correctly picks up time from diverse keys."""
    coordinator = MagicMock()
    now = dt_util.now()

    # Simulate KVV data using 'departure_current'
    coordinator.data = [
        {
            "line": "S51",
            "destination": "Karlsruhe Albtalbahnhof",
            "platform": "2",
            "departure_current": "15:46",
            "departure_timestamp": now.timestamp() + 3600,  # 1 hour in future
            "delay": "1",
        }
    ]
    coordinator.config_entry = mock_config_entry
    coordinator.last_update = now
    coordinator.api_url = "dbf.finalrewind.org"
    coordinator.via_stations_logic = "OR"

    sensor = DBInfoSensor(
        coordinator, mock_config_entry, "Karlsruhe Hbf", [], "", "", True
    )

    # Check extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert any(
        "S51 -> Karlsruhe Albtalbahnhof (Pl 2): 15:46 +1" in text
        for text in attrs["next_departures_text"]
    )


@pytest.mark.asyncio
async def test_custom_text_view_template(hass, mock_config_entry):
    """Test that next_departures_text correctly formats with custom template."""
    coordinator = MagicMock()
    now = dt_util.now()

    coordinator.data = [
        {
            "line": "S51",
            "destination": "Karlsruhe Albtalbahnhof",
            "platform": "2",
            "departure_current": "15:46",
            "departure_timestamp": now.timestamp() + 3600,
            "delay": "1",
        }
    ]

    mock_config_entry.options = {
        "text_view_template": "{line};{destination};{platform};{time}"
    }

    coordinator.config_entry = mock_config_entry
    coordinator.last_update = now
    coordinator.api_url = "dbf.finalrewind.org"
    coordinator.via_stations_logic = "OR"

    sensor = DBInfoSensor(
        coordinator, mock_config_entry, "Karlsruhe Hbf", [], "", "", True
    )

    # Check extra_state_attributes
    attrs = sensor.extra_state_attributes
    print(attrs["next_departures_text"])
    assert any(
        "S51;Karlsruhe Albtalbahnhof;2;15:46" in text
        for text in attrs["next_departures_text"]
    )

    # test missing key in format avoids crash
    mock_config_entry.options = {
        "text_view_template": "{line};{destination};{unknown_key};{time}"
    }

    sensor2 = DBInfoSensor(
        coordinator, mock_config_entry, "Karlsruhe Hbf", [], "", "", True
    )
    attrs2 = sensor2.extra_state_attributes
    assert any(
        "S51;Karlsruhe Albtalbahnhof;{unknown_key};15:46" in text
        for text in attrs2["next_departures_text"]
    )

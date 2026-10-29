from unittest.mock import MagicMock
import pytest
from custom_components.db_infoscreen.sensor import DBInfoScreenWatchdogSensor
from custom_components.db_infoscreen.const import CONF_STATION


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {CONF_STATION: "München Hbf"}
    entry.title = "München Hbf"
    entry.options = {}
    return entry


@pytest.fixture
def mock_coordinator(mock_config_entry):
    coordinator = MagicMock()
    coordinator.data = []
    coordinator.config_entry = mock_config_entry
    coordinator.detailed = True
    return coordinator


def test_watchdog_no_data(mock_coordinator, mock_config_entry):
    sensor = DBInfoScreenWatchdogSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == "No Departures"


def test_watchdog_no_route(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [{"train": "ICE 1", "route": []}]
    sensor = DBInfoScreenWatchdogSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == "No Route Data"


def test_watchdog_station_not_found(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "train": "ICE 1",
            "route": [{"name": "A"}, {"name": "B"}],
            # "München Hbf" not in route
        }
    ]
    sensor = DBInfoScreenWatchdogSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == "Trip Origin / First Stop"


def test_watchdog_valid_previous(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "train": "ICE 1",
            "route": [
                {"name": "Augsburg Hbf", "dep_delay": 5},
                {"name": "München-Pasing", "dep_delay": 2},
                {"name": "München Hbf"},  # Index 2
            ],
        }
    ]
    sensor = DBInfoScreenWatchdogSensor(mock_coordinator, mock_config_entry)

    # Should pick index 1 (München-Pasing)
    assert sensor.native_value == "München-Pasing: +2 min"
    attrs = sensor.extra_state_attributes
    assert attrs["previous_station_name"] == "München-Pasing"
    assert attrs["previous_delay"] == 2


def test_watchdog_on_time(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "train": "ICE 1",
            "route": [
                {"name": "Previous Station", "dep_delay": 0},
                {"name": "München Hbf"},
            ],
        }
    ]
    sensor = DBInfoScreenWatchdogSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == "Previous Station: On Time"

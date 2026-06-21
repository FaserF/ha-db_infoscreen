from unittest.mock import MagicMock
import pytest
from custom_components.db_infoscreen.sensor import DBInfoSensor
from custom_components.db_infoscreen.binary_sensor import DBInfoScreenElevatorBinarySensor
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"station": "München Hbf"}
    entry.title = "München Hbf"
    entry.options = {}
    return entry


@pytest.fixture
def mock_coordinator(mock_config_entry):
    coordinator = MagicMock()
    coordinator.data = []
    coordinator.config_entry = mock_config_entry
    coordinator.station = "München Hbf"
    coordinator.station_messages = [
        {"text": "Signalstörung", "type": "delay", "train": "S 1"},
        {"text": "Aufzug Gleis 1 defekt", "type": "qos", "train": "S 2"},
    ]
    coordinator.raw_elevator_issues = [
        "Aufzug Gleis 1 defekt",
    ]
    return coordinator


def test_station_messages_sensor_attribute(mock_coordinator, mock_config_entry):
    """Test that the main sensor publishes consolidated station messages."""
    sensor = DBInfoSensor(
        mock_coordinator,
        mock_config_entry,
        "München Hbf",
        via_stations=[],
        direction="",
        platforms="",
        enable_text_view=False,
    )
    attrs = sensor.extra_state_attributes
    assert "station_messages" in attrs
    assert len(attrs["station_messages"]) == 2
    assert attrs["station_messages"][0]["text"] == "Signalstörung"
    assert attrs["station_messages"][1]["text"] == "Aufzug Gleis 1 defekt"


def test_defective_facilities_binary_sensor_attribute(mock_coordinator, mock_config_entry):
    """Test that the elevator binary sensor publishes defective facilities."""
    # Sensor with no platform filter (general)
    sensor_gen = DBInfoScreenElevatorBinarySensor(
        mock_coordinator, mock_config_entry, None
    )
    attrs_gen = sensor_gen.extra_state_attributes
    assert "defective_facilities" in attrs_gen
    assert len(attrs_gen["defective_facilities"]) == 1
    facility = attrs_gen["defective_facilities"][0]
    assert facility["facility_type"] == "elevator"
    assert facility["platform"] == "1"
    assert facility["text"] == "Aufzug Gleis 1 defekt"
    assert facility["status"] == "defective"

    # Sensor for Platform 1
    sensor_p1 = DBInfoScreenElevatorBinarySensor(
        mock_coordinator, mock_config_entry, "1"
    )
    assert sensor_p1.is_on is True
    attrs_p1 = sensor_p1.extra_state_attributes
    assert len(attrs_p1["defective_facilities"]) == 1

    # Sensor for Platform 2 (no issue)
    sensor_p2 = DBInfoScreenElevatorBinarySensor(
        mock_coordinator, mock_config_entry, "2"
    )
    assert sensor_p2.is_on is False
    attrs_p2 = sensor_p2.extra_state_attributes
    assert len(attrs_p2["defective_facilities"]) == 0

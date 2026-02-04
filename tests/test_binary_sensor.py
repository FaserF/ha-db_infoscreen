from unittest.mock import MagicMock
import pytest
from custom_components.db_infoscreen.binary_sensor import DBInfoScreenElevatorBinarySensor

@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = []
    return coordinator

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    return entry

def test_elevator_sensor_no_issues(mock_coordinator, mock_config_entry):
    sensor = DBInfoScreenElevatorBinarySensor(mock_coordinator, mock_config_entry, "1")
    assert sensor.is_on is False
    assert sensor.extra_state_attributes["issue_count"] == 0

def test_elevator_sensor_platform_match(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "messages": {
                "qos": [{"text": "Aufzug zu Gleis 1 defekt"}]
            }
        }
    ]

    # Sensor for Platform 1
    sensor_p1 = DBInfoScreenElevatorBinarySensor(mock_coordinator, mock_config_entry, "1")
    assert sensor_p1.is_on is True
    assert "Aufzug zu Gleis 1 defekt" in sensor_p1.extra_state_attributes["issues"]

    # Sensor for Platform 2 (Should not trigger)
    sensor_p2 = DBInfoScreenElevatorBinarySensor(mock_coordinator, mock_config_entry, "2")
    assert sensor_p2.is_on is False

def test_elevator_sensor_general_message(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "messages": {
                "qos": [{"text": "Alle Aufzüge im Bahnhof gestört"}]
            }
        }
    ]

    # Should trigger for specific platform too if no platform is mentioned in text
    sensor_p1 = DBInfoScreenElevatorBinarySensor(mock_coordinator, mock_config_entry, "1")
    assert sensor_p1.is_on is False
    assert len(sensor_p1.extra_state_attributes["issues"]) == 0

def test_elevator_sensor_keywords(mock_coordinator, mock_config_entry):
    mock_coordinator.data = [
        {
            "messages": {
                "qos": [
                    {"text": "Rolltreppe zu Gleis 5 außer Betrieb"},
                    {"text": "Lift defekt (Gleis 5)"}
                ]
            }
        }
    ]

    sensor_p5 = DBInfoScreenElevatorBinarySensor(mock_coordinator, mock_config_entry, "5")
    assert sensor_p5.is_on is True
    assert len(sensor_p5.extra_state_attributes["issues"]) == 2

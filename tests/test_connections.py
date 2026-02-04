from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator
from homeassistant.core import HomeAssistant

@pytest.fixture
def mock_coordinator(hass):
    config_entry = MagicMock()
    config_entry.data = {"station": "Karlsruhe Hbf"}
    config_entry.options = {}
    coordinator = DBInfoScreenCoordinator(hass, config_entry)
    return coordinator

@pytest.mark.asyncio
async def test_track_connection_logic(hass, mock_coordinator):
    """Test that cascaded API call works for connection tracking."""

    # 1. Setup tracked connection
    mock_coordinator.tracked_connections["ICE 1"] = {
        "change_station": "Mannheim Hbf",
        "next_train_id": "ICE 2"
    }

    # 2. Mock departures for current station (Karlsruhe)
    current_station_data = {
        "departures": [
            {
                "train": "ICE 1",
                "destination": "Berlin",
                "scheduledDeparture": "10:00",
                "departure_timestamp": 1700000000,
                "route": [{"name": "Karlsruhe Hbf"}, {"name": "Mannheim Hbf"}, {"name": "Frankfurt Hbf"}]
            }
        ]
    }

    # 3. Mock departures for change station (Mannheim)
    change_station_data = {
        "departures": [
            {
                "train": "ICE 2",
                "destination": "Frankfurt",
                "scheduledDeparture": "10:30",
                "delayDeparture": 5,
                "platform": "5"
            }
        ]
    }

    # 4. Mock API calls
    from tests.common import patch_session

    # We need a side effect for patch_session to return different data for different stations
    def api_side_effect(url, **kwargs):
        if "Mannheim" in url:
            return change_station_data
        return current_station_data

    with patch_session(side_effect=api_side_effect):
        data = await mock_coordinator._async_update_data()

        # Verify ICE 1 has connection info
        assert len(data) == 1
        assert data[0]["train"] == "ICE 1"
        assert "connection_info" in data[0]
        assert data[0]["connection_info"]["target_train"] == "ICE 2"
        assert data[0]["connection_info"]["target_platform"] == "5"
        assert data[0]["connection_info"]["target_delay"] == 5

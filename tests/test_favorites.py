from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from datetime import timedelta
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_FAVORITE_TRAINS,
    CONF_STATION,
)
from homeassistant.util import dt as dt_util

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {CONF_STATION: "München Hbf"}
    entry.options = {CONF_FAVORITE_TRAINS: ""}
    return entry

@pytest.mark.asyncio
async def test_coordinator_favorite_trains_filter(hass, mock_config_entry):
    """Test that departures are filtered by favorite trains."""
    mock_config_entry.options[CONF_FAVORITE_TRAINS] = "ICE 1, RE 2"
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    mock_data = {
        "departures": [
            {"scheduledDeparture": "10:00", "destination": "Berlin", "train": "ICE 1"},
            {"scheduledDeparture": "10:10", "destination": "Nürnberg", "train": "ICE 500"},
            {"scheduledDeparture": "10:20", "destination": "Salzburg", "train": "RE 2 (Regio)"},
        ]
    }

    from tests.common import patch_session
    with patch_session(mock_data):
        # Explicitly make raise_for_status a no-op to avoid RuntimeWarning
        # (patch_session should have done this, but being safe)
        with patch("custom_components.db_infoscreen.DBInfoScreenCoordinator._check_watched_trips", new_callable=AsyncMock):
            data = await coordinator._async_update_data()
            assert len(data) == 2
            assert data[0]["train"] == "ICE 1"
            assert data[1]["train"] == "RE 2 (Regio)"

@pytest.mark.asyncio
async def test_coordinator_favorite_trains_empty(hass, mock_config_entry):
    """Test that no filtering happens if favorite_trains is empty."""
    mock_config_entry.options[CONF_FAVORITE_TRAINS] = ""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    mock_data = {
        "departures": [
            {"scheduledDeparture": "10:00", "train": "ICE 1", "destination": "A"},
            {"scheduledDeparture": "10:10", "train": "ICE 2", "destination": "B"},
        ]
    }

    from tests.common import patch_session
    with patch_session(mock_data):
        with patch("custom_components.db_infoscreen.DBInfoScreenCoordinator._check_watched_trips", new_callable=AsyncMock):
            data = await coordinator._async_update_data()
            assert len(data) == 2

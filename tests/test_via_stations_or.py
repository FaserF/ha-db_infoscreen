from unittest.mock import MagicMock, AsyncMock, patch
from datetime import timedelta
import pytest
from homeassistant.util import dt as dt_util

from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_VIA_STATIONS,
    CONF_VIA_STATIONS_LOGIC,
)
from tests.common import patch_session


@pytest.fixture(autouse=True)
def patch_coordinator():
    """Patch DataUpdateCoordinator to prevent background tasks and simplify tests."""
    with patch(
        "custom_components.db_infoscreen.DataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        yield


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Mainz Hbf",
        CONF_VIA_STATIONS: ["Frankfurt(Main)Hbf", "Frankfurt Hbf (tief)"],
        CONF_VIA_STATIONS_LOGIC: "OR",
    }
    entry.options = {}
    entry.entry_id = "mock_entry_id"
    return entry


@pytest.mark.asyncio
async def test_coordinator_via_stations_or_logic(hass, mock_config_entry):
    """Test that multiple via stations work with OR logic."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Verify that the via parameter is NOT in the api_url (moving to client-side filtering)
    # Actually, as per current code, it IS in the api_url.

    now = dt_util.now()
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "destination": "Darmstadt Hbf",
                "train": "S 8",
                "via": ["Frankfurt Hbf (tief)", "Frankfurt(M)Ostendstraße"],
                "route": [
                    {"name": "Frankfurt Hbf (tief)"},
                    {"name": "Frankfurt(M)Ostendstraße"},
                ],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=15)).strftime("%H:%M"),
                "destination": "Aschaffenburg Hbf",
                "train": "RE 55",
                "via": ["Frankfurt(Main)Hbf", "Hanau Hbf"],
                "route": [{"name": "Frankfurt(Main)Hbf"}, {"name": "Hanau Hbf"}],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=20)).strftime("%H:%M"),
                "destination": "Mannheim Hbf",
                "train": "RE 70",
                "via": ["Biblis", "Ladenburg"],
                "route": [{"name": "Biblis"}, {"name": "Ladenburg"}],
            },
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()

        # We expect only the first two trains (Frankfurt variants)
        assert len(data) == 2
        destinations = [d["destination"] for d in data]
        assert "Darmstadt Hbf" in destinations
        assert "Aschaffenburg Hbf" in destinations
        assert "Mannheim Hbf" not in destinations

    # Also verify that the via parameter is removed from the URL in the new implementation
    assert "via=" not in coordinator.api_url

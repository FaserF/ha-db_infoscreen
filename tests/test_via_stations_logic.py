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


@pytest.mark.asyncio
async def test_via_single_station_server_side(hass):
    """Test that a single via station uses the API parameter."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Mainz Hbf",
        CONF_VIA_STATIONS: ["Frankfurt(Main)Hbf"],
    }
    entry.options = {}
    entry.entry_id = "mock_entry_id"

    coordinator = DBInfoScreenCoordinator(hass, entry)

    # Check URL: should contain via parameter
    assert "via=Frankfurt%28Main%29Hbf" in coordinator.api_url

    now = dt_util.now()
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "destination": "Hanau Hbf",
                "train": "RE 54",
                "via": ["Frankfurt(Main)Hbf", "Offenbach(Main)Hbf"],
                "route": [{"name": "Frankfurt(Main)Hbf"}],
            }
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 1


@pytest.mark.asyncio
async def test_via_multiple_stations_or_local(hass):
    """Test that multiple via stations use local OR filtering and no API param."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Mainz Hbf",
        CONF_VIA_STATIONS: ["Frankfurt(Main)Hbf", "Darmstadt Hbf"],
        CONF_VIA_STATIONS_LOGIC: "OR",
    }
    entry.options = {}
    entry.entry_id = "mock_entry_id"

    coordinator = DBInfoScreenCoordinator(hass, entry)

    # Check URL: should NOT contain via parameter
    assert "via=" not in coordinator.api_url

    now = dt_util.now()
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "destination": "Aschaffenburg",
                "train": "RE 55",
                "via": ["Frankfurt(Main)Hbf"],
                "route": [{"name": "Frankfurt(Main)Hbf"}],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=15)).strftime("%H:%M"),
                "destination": "Heidelberg",
                "train": "RB 68",
                "via": ["Darmstadt Hbf"],
                "route": [{"name": "Darmstadt Hbf"}],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=20)).strftime("%H:%M"),
                "destination": "Koblenz",
                "train": "RE 2",
                "via": ["Bingen"],
                "route": [{"name": "Bingen"}],
            },
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # Should include Aschaffenburg (via Frankfurt) and Heidelberg (via Darmstadt)
        data = list(data)
        assert len(data) == 2
        dests = [d["destination"] for d in data]
        assert "Aschaffenburg" in dests
        assert "Heidelberg" in dests
        assert "Koblenz" not in dests


@pytest.mark.asyncio
async def test_via_multiple_stations_and_local(hass):
    """Test that multiple via stations use local AND filtering."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Mainz Hbf",
        CONF_VIA_STATIONS: ["Frankfurt(Main)Hbf", "Hanau Hbf"],
        CONF_VIA_STATIONS_LOGIC: "AND",
    }
    entry.options = {}
    entry.entry_id = "mock_entry_id"

    coordinator = DBInfoScreenCoordinator(hass, entry)

    # Check URL: should NOT contain via parameter
    assert "via=" not in coordinator.api_url

    now = dt_util.now()
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "destination": "Fulda",
                "train": "RE 50",
                "via": ["Frankfurt(Main)Hbf", "Hanau Hbf", "Wächtersbach"],
                "route": [{"name": "Frankfurt(Main)Hbf"}, {"name": "Hanau Hbf"}],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=15)).strftime("%H:%M"),
                "destination": "Aschaffenburg",
                "train": "RE 55",
                "via": ["Frankfurt(Main)Hbf", "Offenbach"],
                "route": [{"name": "Frankfurt(Main)Hbf"}],
            },
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # Only Fulda passes through BOTH Frankfurt AND Hanau
        data = list(data)
        assert len(data) == 1
        assert data[0]["destination"] == "Fulda"


@pytest.mark.asyncio
async def test_via_multiple_stations_and_local_no_match(hass):
    """Test that AND logic excludes departures that don't match ALL via stations."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Mainz Hbf",
        CONF_VIA_STATIONS: ["Frankfurt(Main)Hbf", "Hanau Hbf"],
        CONF_VIA_STATIONS_LOGIC: "AND",
    }
    entry.options = {}
    entry.entry_id = "mock_entry_id"

    coordinator = DBInfoScreenCoordinator(hass, entry)

    now = dt_util.now()
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "destination": "Aschaffenburg",
                "train": "RE 55",
                # Only matches Frankfurt, missing Hanau
                "via": ["Frankfurt(Main)Hbf", "Offenbach"],
                "route": [{"name": "Frankfurt(Main)Hbf"}],
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=15)).strftime("%H:%M"),
                "destination": "Bamberg",
                "train": "RE 54",
                # Only matches Hanau, missing Frankfurt
                "via": ["Hanau Hbf", "Würzburg"],
                "route": [{"name": "Hanau Hbf"}],
            },
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # Neither train passes through BOTH stations
        data = list(data)
        assert len(data) == 0

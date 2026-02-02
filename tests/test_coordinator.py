from unittest.mock import MagicMock, AsyncMock, patch
from datetime import timedelta
import pytest
from homeassistant.util import dt as dt_util
from contextlib import contextmanager
import copy
import os

from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
    CONF_VIA_STATIONS,
    CONF_DATA_SOURCE,
    CONF_DETAILED,
    CONF_HIDE_LOW_DELAY,
)


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
        CONF_STATION: "Karlsruhe Hbf",
        CONF_UPDATE_INTERVAL: 2,
    }
    entry.options = {
        CONF_NEXT_DEPARTURES: 5,
    }
    return entry


@contextmanager
def patch_session(mock_data, side_effect=None):
    """Patch the async_get_clientsession to return a mock session with data."""
    with patch(
        "custom_components.db_infoscreen.async_get_clientsession"
    ) as mock_get_session:
        # Mock Response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_data)

        # Async context manager protocol
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock Session
        mock_session = MagicMock()

        # session.get needs to return a context manager directly, not a coroutine
        def mock_get(*args, **kwargs):
            if side_effect:
                res = side_effect(*args, **kwargs)
                # If side_effect returns raw data, wrap it in an ACM shim
                if isinstance(res, (dict, list)):
                    shim = MagicMock()
                    shim.status = 200
                    shim.raise_for_status = MagicMock()
                    shim.json = AsyncMock(return_value=res)
                    shim.__aenter__ = AsyncMock(return_value=shim)
                    shim.__aexit__ = AsyncMock(return_value=None)
                    return shim
                return res
            return mock_response

        mock_session.get = MagicMock(side_effect=mock_get)

        mock_get_session.return_value = mock_session
        yield mock_session


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_url_encoding(hass, mock_config_entry):
    """Test correctly encoding of station and via parameters."""
    mock_config_entry.data[CONF_VIA_STATIONS] = ["Hagsfeld Jenaer Straße"]
    mock_config_entry.data[CONF_STATION] = "Hagsfeld Reitschulschlag, Karlsruhe"

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    expected_station = "Hagsfeld%20Reitschulschlag,%20Karlsruhe"
    assert expected_station in coordinator.api_url
    assert "via=Hagsfeld%20Jenaer%20Stra%C3%9Fe" in coordinator.api_url


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_options_in_url(hass, mock_config_entry):
    """Test that options are correctly correctly added to the URL."""
    mock_config_entry.options[CONF_DETAILED] = True
    mock_config_entry.options[CONF_HIDE_LOW_DELAY] = True

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    assert "detailed=1" in coordinator.api_url
    assert "hidelowdelay=1" in coordinator.api_url


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_data_source_params(hass, mock_config_entry):
    """Test that data source mapping works."""
    mock_config_entry.options[CONF_DATA_SOURCE] = "NVBW"  # efa=NVBW

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    assert "efa=NVBW" in coordinator.api_url

    mock_config_entry.options[CONF_DATA_SOURCE] = "ÖBB"  # hafas=ÖBB
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    assert (
        "hafas=%C3%96BB" in coordinator.api_url
        or "hafas=\xc3\x96BB" in coordinator.api_url
    )


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_update_data(hass, mock_config_entry):
    """Test updating data."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Test Dest",
                "train": "ICE 123",
                "delayDeparture": 0,
            }
        ]
    }

    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert data[0]["destination"] == "Test Dest"


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_exclude_cancelled(hass, mock_config_entry):
    """Test excluding cancelled trains."""
    from custom_components.db_infoscreen.const import CONF_EXCLUDE_CANCELLED

    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Valid Train",
                "train": "ICE 1",
                "cancelled": False,
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Cancelled Train",
                "train": "ICE 2",
                "cancelled": True,
            },
        ]
    }

    # Test Default (include cancelled)
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2

    # Test Exclude Cancelled
    mock_config_entry.options[CONF_EXCLUDE_CANCELLED] = True
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert data[0]["destination"] == "Valid Train"


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_occupancy(hass, mock_config_entry):
    """Test parsing occupancy data."""
    from custom_components.db_infoscreen.const import CONF_SHOW_OCCUPANCY

    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Test Dest",
                "train": "ICE 1",
                "occupancy": {"1": 1, "2": 4},  # 1st class low, 2nd class full
            }
        ]
    }

    # Test Default (Occupancy Disabled)
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(copy.deepcopy(mock_data)):
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert "occupancy" not in data[0]

    # Test Occupancy Enabled
    mock_config_entry.options[CONF_SHOW_OCCUPANCY] = True
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(copy.deepcopy(mock_data)):
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert data[0]["occupancy"] == {"1": 1, "2": 4}


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_platform_change(hass, mock_config_entry):
    """Test platform change detection."""
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Changed Platform",
                "train": "ICE 1",
                "platform": "5",
                "scheduledPlatform": "4",
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Same Platform",
                "train": "ICE 2",
                "platform": "1",
                "scheduledPlatform": "1",
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2
        assert data[0]["changed_platform"] is True
        assert data[1]["changed_platform"] is False


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_wagon_order(hass, mock_config_entry):
    """Test wagon order and sector extraction."""
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "With Sectors",
                "train": "ICE 1",
                "platform": "Gl. 5 A-C",
                "wagonorder": True,
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "No Sectors",
                "train": "ICE 2",
                "platform": "Standard",
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2
        # Test 1: Full info
        assert data[0]["wagon_order"] is True
        assert data[0]["platform_sectors"] == "A-C"
        # Test 2: Missing info
        assert "wagon_order" not in data[1]
        assert "platform_sectors" not in data[1]


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_qos(hass, mock_config_entry):
    """Test QoS parsing and facilities extraction."""
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "QoS Train",
                "train": "ICE 1",
                "qos": {"wifi": True},
                "messages": {
                    "qos": [
                        {"text": "Bistro im Zug geschlossen", "code": "80"},
                        {"text": "WLAN im gesamten Zug gestört", "code": "82"},
                    ]
                },
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "No QoS",
                "train": "ICE 2",
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2
        # Test 1: QoS and Facilities
        assert data[0]["qos"] == {"wifi": True}
        assert data[0]["facilities"] == {"bistro": False, "wifi": False}
        # Test 2: No QoS
        assert "qos" not in data[1]
        assert "facilities" not in data[1]


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_route_details(hass, mock_config_entry):
    """Test route details parsing."""
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Route Train",
                "train": "ICE 1",
                "route": [
                    {"name": "Stop A", "arr_delay": 5},
                    {"name": "Stop B", "dep_delay": 0},
                    {"name": "Stop C"},  # No delay info
                ],
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Simple Route",
                "train": "ICE 2",
                "route": ["Simple A", "Simple B"],
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2
        # Test 1: Detailed Route
        details = data[0]["route_details"]
        assert len(details) == 3
        assert details[0] == {"name": "Stop A", "arr_delay": 5}
        assert details[1] == {"name": "Stop B", "dep_delay": 0}
        assert details[2] == {"name": "Stop C"}
        # Test 2: Simple Route
        simple_details = data[1]["route_details"]
        assert len(simple_details) == 2
        assert simple_details[0] == {"name": "Simple A"}
        assert simple_details[1] == {"name": "Simple B"}


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="CI Frame Helper Issue"
)
@pytest.mark.asyncio
async def test_coordinator_trip_id(hass, mock_config_entry):
    """Test trip ID parsing."""
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "ID Train",
                "train": "ICE 1",
                "trainId": "123456789",  # Common field
            },
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "No ID",
                "train": "ICE 2",
                # No ID field
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        assert len(data) == 2
        # Test 1: Trip ID present
        assert data[0]["trip_id"] == "123456789"
        # Test 2: Trip ID missing
        assert data[1]["trip_id"] is None

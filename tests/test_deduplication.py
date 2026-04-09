from unittest.mock import MagicMock
from datetime import timedelta
import pytest
from homeassistant.util import dt as dt_util

from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_DEDUPLICATE_DEPARTURES,
    CONF_DEDUPLICATE_KEY,
)
from tests.common import patch_session


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the global RESPONSE_CACHE between tests."""
    from custom_components.db_infoscreen import RESPONSE_CACHE

    RESPONSE_CACHE.clear()
    yield
    RESPONSE_CACHE.clear()


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Karlsruhe Hbf",
    }
    entry.options = {
        CONF_NEXT_DEPARTURES: 5,
        CONF_DEDUPLICATE_DEPARTURES: True,
    }
    entry.entry_id = "mock_entry_id"
    return entry


@pytest.mark.asyncio
async def test_deduplication_default_key(hass, mock_config_entry):
    """Test deduplication with default key (DB IRIS style)."""
    now = dt_util.now() + timedelta(minutes=15)
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": now.strftime("%Y-%m-%dT%H:%M"),
                "destination": "Berlin",
                "line": "ICE 1",
                "journeyID": "12345",
            },
            {
                "scheduledDeparture": (now + timedelta(seconds=30)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Berlin",
                "line": "ICE 1",
                "journeyID": "12345",  # Same ID, short time diff
            },
            {
                "scheduledDeparture": (now + timedelta(minutes=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Berlin",
                "line": "ICE 1",
                "journeyID": "12345",  # Same ID, but > 120s diff
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # Should have 2 departures:
        # 1. The first one (or second) from the 30s pair
        # 2. The third one (10 min later)
        assert len(data) == 2


@pytest.mark.asyncio
async def test_deduplication_custom_key_kvv(hass, mock_config_entry):
    """Test deduplication with custom key for KVV (as requested in #116)."""
    mock_config_entry.options[CONF_DEDUPLICATE_KEY] = "{line}"

    now = dt_util.now() + timedelta(minutes=15)
    # KVV style data where journeyID is missing/null but line is same
    mock_data = {
        "departures": [
            {
                "datetime": int(now.timestamp()),
                "destination": "Rheinstetten",
                "line": "S2",
                "platform": "3",
            },
            {
                "datetime": int(now.timestamp()) + 60,
                "destination": "Rheinstetten",
                "line": "S2",
                "platform": "1",
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # With {line} as key, they should be deduplicated
        assert len(data) == 1


@pytest.mark.asyncio
async def test_deduplication_fallback(hass, mock_config_entry):
    """Test deduplication fallback when key resolving yields empty string."""
    mock_config_entry.options[CONF_DEDUPLICATE_KEY] = "{non_existent_field}"

    now = dt_util.now() + timedelta(minutes=15)
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": now.strftime("%Y-%m-%dT%H:%M"),
                "destination": "Berlin",
                "line": "ICE 1",
            },
            {
                "scheduledDeparture": (now + timedelta(seconds=10)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Berlin",
                "line": "ICE 1",
            },
        ]
    }

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch_session(mock_data):
        data = await coordinator._async_update_data()
        # Should fallback to (line, destination) and deduplicate
        assert len(data) == 1

"""Test the DB Infoscreen coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.util import dt as dt_util

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


async def test_coordinator_url_encoding(hass, mock_config_entry):
    """Test correctly encoding of station and via parameters."""
    # Test case from user feedback: "Hagsfeld Jenaer Straße"
    mock_config_entry.data[CONF_VIA_STATIONS] = ["Hagsfeld Jenaer Straße"]
    mock_config_entry.data[CONF_STATION] = "Hagsfeld Reitschulschlag, Karlsruhe"

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Check if station is encoded correctly (spaces -> %20, Comma -> %2C)
    # quote_plus("Hagsfeld Reitschulschlag, Karlsruhe") -> Hagsfeld+Reitschulschlag%2C+Karlsruhe
    # The code manually replaces + with %20 for the station name part effectively.
    # We should verify the final URL.

    expected_station = "Hagsfeld%20Reitschulschlag,%20Karlsruhe"  # based on code logic
    assert expected_station in coordinator.api_url

    # Check VIA encoding: This was the fix. Spaces should be "+" now, not "%20".
    # quote_plus("Hagsfeld Jenaer Straße") -> Hagsfeld+Jenaer+Stra%C3%9Fe
    assert "via=Hagsfeld+Jenaer+Stra%C3%9Fe" in coordinator.api_url


async def test_coordinator_options_in_url(hass, mock_config_entry):
    """Test that options are correctly correctly added to the URL."""
    mock_config_entry.options[CONF_DETAILED] = True
    mock_config_entry.options[CONF_HIDE_LOW_DELAY] = True

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    assert "detailed=1" in coordinator.api_url
    assert "hidelowdelay=1" in coordinator.api_url


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
    )  # Check encoding


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

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        data = await coordinator._async_update_data()

        assert len(data) == 1
        assert data[0]["destination"] == "Test Dest"


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
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        data = await coordinator._async_update_data()
        assert len(data) == 2

    # Test Exclude Cancelled
    mock_config_entry.options[CONF_EXCLUDE_CANCELLED] = True
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert data[0]["destination"] == "Valid Train"

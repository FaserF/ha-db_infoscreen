"""Tests for stability and security scenarios."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = AsyncMock()
    entry.data = {
        CONF_STATION: "Karlsruhe Hbf",
        CONF_UPDATE_INTERVAL: 2,
    }
    entry.options = {
        CONF_NEXT_DEPARTURES: 5,
    }
    return entry


@pytest.mark.asyncio
async def test_coordinator_handles_api_errors(hass, mock_config_entry):
    """Test that the coordinator handles API errors gracefully without crashing."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Simulate a network error
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.side_effect = Exception("Network Error")

        # Should not raise exception
        data = await coordinator._async_update_data()
        assert data == [] or data is None

    # Simulate a 500 error
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")
        mock_get.return_value.__aenter__.return_value = mock_response

        data = await coordinator._async_update_data()
        assert data == [] or data is None


@pytest.mark.asyncio
async def test_coordinator_handles_malformed_json(hass, mock_config_entry):
    """Test handling of invalid JSON response."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        # json() is awaited in code, so mock it as AsyncMock or MagicMock returning coroutine
        mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        mock_get.return_value.__aenter__.return_value = mock_response

        data = await coordinator._async_update_data()
        assert data == [] or data is None


@pytest.mark.asyncio
async def test_input_sanitization(hass, mock_config_entry):
    """Test that special characters in station names don't crash or cause injection-like issues."""
    # While we use quote_plus, we should verify that extremely weird inputs don't crash the logic
    # Injected control characters or weird unicode
    mock_config_entry.data[CONF_STATION] = "Karlsruhe\nNewHeader: Injected"

    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Ensure URL is constructed without newlines injection
    assert "\n" not in coordinator.api_url
    assert "Karlsruhe" in coordinator.api_url


@pytest.mark.asyncio
async def test_large_response_handling(hass, mock_config_entry):
    """Test handling of very large responses (DoS protection simulation)."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Create a massive fake response
    large_data = {
        "departures": [
            {"train": f"ICE {i}", "destination": "Berlin"} for i in range(1000)
        ]
    }

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=large_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        # The coordinator has logic to limit JSON size (MAX_SIZE_BYTES = 16000)
        # Verify it respects that limit (it should return a truncated list)
        data = await coordinator._async_update_data()

        # Just check that it didn't return 1000 items (which would be huge)
        # Handle None safely
        assert data is None or len(data) <= 100  # Definitely filtered/truncated

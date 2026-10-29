"""Tests for stability and security scenarios."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    CONF_STATION,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
)
from tests.common import patch_session


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
    entry.entry_id = "mock_entry_id"
    return entry


@pytest.mark.asyncio
async def test_coordinator_handles_api_errors(hass, mock_config_entry):
    """Test that the coordinator handles API errors gracefully without crashing."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    # Simulate a network error
    def side_effect_error(*args, **kwargs):
        raise Exception("Network Error")

    with patch_session(side_effect=side_effect_error):
        # Should not raise exception
        data = await coordinator._async_update_data()
        assert data == [] or data is None

    # Simulate a 500 error
    def side_effect_500(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        return mock_resp

    with patch_session(side_effect=side_effect_500):
        data = await coordinator._async_update_data()
        assert data == [] or data is None


@pytest.mark.asyncio
async def test_coordinator_handles_malformed_json(hass, mock_config_entry):
    """Test handling of invalid JSON response."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)

    def side_effect_malformed(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        return mock_resp

    with patch_session(side_effect=side_effect_malformed):
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

    with patch_session(mock_data=large_data):
        # The coordinator has logic to limit JSON size (MAX_SIZE_BYTES = 16000)
        # Verify it respects that limit (it should return a truncated list)
        data = await coordinator._async_update_data()

        # Just check that it didn't return 1000 items (which would be huge)
        # Handle None safely
        assert data is None or len(data) <= 100  # Definitely filtered/truncated

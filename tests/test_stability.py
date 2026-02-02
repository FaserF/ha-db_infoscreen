"""Tests for stability and security scenarios."""

from contextlib import contextmanager
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


@contextmanager
def patch_session(mock_data=None, side_effect=None):
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

        # session.get needs to return a context manager directly
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

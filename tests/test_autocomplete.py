import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.db_infoscreen.utils import (
    async_get_stations,
    find_station_matches,
    CACHE_KEY_DATA,
)


# Simpler hass fixture for autocomplete tests (doesn't need config_entries mocking)
@pytest.fixture
def hass():
    """Mock Hass for autocomplete tests."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    return mock_hass


@pytest.mark.asyncio
async def test_async_get_stations_download(hass):
    """Test downloading stations when not cached."""
    # Mock the aiohttp_client module's async_get_clientsession function
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(
        return_value='stations=["Hamburg Hbf", "München Hbf"];'
    )
    mock_response.raise_for_status = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.dict(
        "sys.modules",
        {
            "homeassistant.helpers.aiohttp_client": MagicMock(
                async_get_clientsession=MagicMock(return_value=mock_session)
            )
        },
    ):
        # Execute
        stations = await async_get_stations(hass)

        assert "Hamburg Hbf" in stations
        assert "München Hbf" in stations
        assert CACHE_KEY_DATA in hass.data


def test_find_station_matches():
    """Test the matching logic (exact, starts-with, contains, fuzzy)."""
    stations = ["München Hbf", "München Ost", "Hamburg Hbf", "Berlin Hbf"]

    # Exact match
    assert find_station_matches(stations, "Hamburg Hbf") == ["Hamburg Hbf"]

    # Starts with
    assert "München Hbf" in find_station_matches(stations, "München")
    assert "München Ost" in find_station_matches(stations, "München")

    # Starts with (these are NOT fuzzy matches)
    assert "Hamburg Hbf" in find_station_matches(stations, "Hamburg")
    assert "Berlin Hbf" in find_station_matches(stations, "Berlin")

    # Fuzzy match (typos/misspellings)
    assert "München Hbf" in find_station_matches(stations, "Muenchen")
    assert "Hamburg Hbf" in find_station_matches(stations, "Hambur")

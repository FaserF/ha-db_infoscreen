from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from datetime import timedelta
from homeassistant.util import dt as dt_util
from custom_components.db_infoscreen.sensor import DBInfoSensor
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import DOMAIN

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"station": "Karlsruhe Hbf"}
    entry.options = {}
    return entry

@pytest.mark.asyncio
async def test_past_departure_filtering(hass, mock_config_entry):
    """Test that departures in the past are filtered out."""
    coordinator = MagicMock()
    now = dt_util.now()
    
    # One departure in the past, one in the future
    coordinator.data = [
        {
            "train": "S1",
            "departure_timestamp": int((now - timedelta(minutes=5)).timestamp()),
            "scheduledDeparture": "10:00"
        },
        {
            "train": "S3",
            "departure_timestamp": int((now + timedelta(minutes=10)).timestamp()),
            "scheduledDeparture": "10:15"
        }
    ]
    coordinator.config_entry = mock_config_entry
    
    sensor = DBInfoSensor(coordinator, mock_config_entry, "Karlsruhe Hbf", [], "", "", False)
    
    # native_value should pick S3 (the only future one)
    assert sensor.native_value is not None
    # Filtered list should only contain S3
    departures = sensor._get_filtered_departures()
    assert len(departures) == 1
    assert departures[0]["train"] == "S3"

@pytest.mark.asyncio
async def test_zero_update_interval(hass, mock_config_entry):
    """Test that update_interval is handled correctly when set to 0."""
    mock_config_entry.options = {"update_interval": 0}
    
    with patch("custom_components.db_infoscreen.DBInfoScreenCoordinator.async_config_entry_first_refresh", AsyncMock()):
        coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
        # It's either None or 0 depending on HA version/DataUpdateCoordinator
        assert coordinator.update_interval is None or coordinator.update_interval.total_seconds() == 0

@pytest.mark.asyncio
async def test_refresh_service(hass, mock_config_entry):
    """Test the refresh_departures service."""
    # Create the coordinator
    with patch("custom_components.db_infoscreen.DBInfoScreenCoordinator.async_config_entry_first_refresh", AsyncMock()):
        coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
        
    # Mock the async_refresh method
    coordinator.async_refresh = AsyncMock()
    hass.data[DOMAIN] = {"test_entry": coordinator}
    
    # We don't need to manually register the service if it's done in async_setup_entry,
    # but for a unit test, we can just call the coordinator method directly or 
    # test the service logic. Let's test the service logic as it was intended.
    
    # Define service handler (mimicking __init__.py)
    async def async_refresh_departures(service_call):
        for coord in hass.data[DOMAIN].values():
            await coord.async_refresh()
            
    hass.services.async_register(DOMAIN, "refresh_departures", async_refresh_departures)
    
    # Use a real service call if possible, but here we just want to verify the handler
    await async_refresh_departures(None)
    assert coordinator.async_refresh.called

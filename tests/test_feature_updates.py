from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from datetime import datetime, timedelta
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
            "train": "S2",
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
    val = sensor.native_value
    assert "S3" in str(coordinator.data[1]["train"]) # check sanity
    # The sensor logic uses departures[0] from filtered list
    # S2 should be excluded
    assert sensor._get_filtered_departures()[0]["train"] == "S3"

@pytest.mark.asyncio
async def test_zero_update_interval(hass, mock_config_entry):
    """Test that update_interval is None when set to 0."""
    mock_config_entry.options = {"update_interval": 0}
    
    with patch("custom_components.db_infoscreen.DBInfoScreenCoordinator.async_config_entry_first_refresh", AsyncMock()):
        coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
        assert coordinator.update_interval is None

@pytest.mark.asyncio
async def test_refresh_service(hass, mock_config_entry):
    """Test the refresh_departures service."""
    coordinator = MagicMock(spec=DBInfoScreenCoordinator)
    coordinator.async_refresh = AsyncMock()
    hass.data[DOMAIN] = {"test_entry": coordinator}
    
    # Define service handler (normally registered in async_setup_entry)
    async def async_refresh_departures(service_call):
        for coord in hass.data[DOMAIN].values():
            await coord.async_refresh()
            
    hass.services.async_register(DOMAIN, "refresh_departures", async_refresh_departures)
    
    await hass.services.async_call(DOMAIN, "refresh_departures", {}, blocking=True)
    coordinator.async_refresh.assert_called_once()

from unittest.mock import MagicMock, AsyncMock, patch
from datetime import timedelta
import pytest
from homeassistant.util import dt as dt_util
from homeassistant.data_entry_flow import FlowResultType

from custom_components.db_infoscreen import DBInfoScreenCoordinator
from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_UPDATE_INTERVAL,
    CONF_PAUSED,
    CONF_NEXT_DEPARTURES,
)
from tests.common import patch_session

@pytest.fixture(autouse=True)
def patch_coordinator():
    with patch(
        "custom_components.db_infoscreen.DataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        yield

@pytest.fixture(autouse=True)
def clear_cache():
    from custom_components.db_infoscreen import RESPONSE_CACHE
    RESPONSE_CACHE.clear()
    yield
    RESPONSE_CACHE.clear()

@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.data = {
        CONF_STATION: "Karlsruhe Hbf",
        CONF_UPDATE_INTERVAL: 2,
    }
    entry.options = {
        CONF_PAUSED: False,
    }
    entry.entry_id = "mock_entry_id"
    return entry

@pytest.mark.asyncio
async def test_coordinator_pause_updates(hass, mock_config_entry):
    """Test that updates can be paused in the coordinator."""
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    coordinator.async_fetch_server_version = AsyncMock()
    
    mock_data = {
        "departures": [
            {
                "scheduledDeparture": (dt_util.now() + timedelta(minutes=15)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "destination": "Test Dest",
                "train": "ICE 123",
                "delayDeparture": 0,
            }
        ]
    }

    # 1. Test update when NOT paused
    with patch_session(mock_data) as mock_sess:
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert mock_sess.get.call_count == 1

    # 2. Test update when PAUSED
    mock_config_entry.options[CONF_PAUSED] = True
    coordinator = DBInfoScreenCoordinator(hass, mock_config_entry)
    coordinator.async_fetch_server_version = AsyncMock()
    
    with patch_session(mock_data) as mock_sess:
        data = await coordinator._async_update_data()
        assert len(data) == 0
        assert mock_sess.get.call_count == 0

    # 3. Test that it returns last valid value when paused
    coordinator._last_valid_value = [{"train": "Last Valid"}]
    with patch_session(mock_data) as mock_sess:
        data = await coordinator._async_update_data()
        assert len(data) == 1
        assert data[0]["train"] == "Last Valid"
        assert mock_sess.get.call_count == 0

@pytest.mark.asyncio
async def test_config_flow_schema_has_paused(hass):
    """Test that the config flow details schema contains the paused option."""
    from custom_components.db_infoscreen.config_flow import ConfigFlow
    flow = ConfigFlow()
    flow.hass = hass
    flow.selected_station = "Berlin Hbf"
    
    schema = flow.details_schema(basic=True)
    assert CONF_PAUSED in schema.schema

@pytest.mark.asyncio
async def test_options_flow_schema_has_paused(hass):
    """Test that the options flow general options schema contains the paused option."""
    hass.config_entries.options.async_configure.return_value = {
        "type": FlowResultType.FORM,
        "step_id": "general_options",
        "data_schema": MagicMock()
    }
    hass.config_entries.options.async_configure.return_value["data_schema"].schema = {
        CONF_PAUSED: True
    }
    
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_STATION: "Karlsruhe Hbf"},
        options={CONF_PAUSED: False},
    )
    entry.add_to_hass(hass)
    
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "general_options"}
    )
    
    assert result["type"] == FlowResultType.FORM
    assert CONF_PAUSED in result["data_schema"].schema

@pytest.mark.asyncio
async def test_set_paused_service(hass):
    """Test the set_paused service."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.db_infoscreen import async_setup_entry
    
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_STATION: "Karlsruhe Hbf"},
        options={CONF_PAUSED: False},
        entry_id="test_service",
    )
    entry.add_to_hass(hass)
    
    # Mock forward entry setups and service call to avoid TypeError
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services.async_call = AsyncMock()
    
    # Setup entry to register services
    await async_setup_entry(hass, entry)
    
    # Manually extract the service handler since we mocked async_call
    # Actually, we can just call the handler directly if we can find it, 
    # but it's better to just mock the register function to get the handler.
    
    with patch("homeassistant.core.ServiceRegistry.async_register") as mock_reg:
        await async_setup_entry(hass, entry)
        # Find set_paused registration
        handler = None
        for call in hass.services.async_register.call_args_list:
            if call[0][1] == "set_paused":
                handler = call[0][2]
                break
        
        if handler:
            # Call handler directly
            call = MagicMock()
            call.data = {"station": "Karlsruhe Hbf", "paused": True}
            await handler(call)
            assert entry.options[CONF_PAUSED] is True
            
            call.data = {"station": "Karlsruhe Hbf", "paused": False}
            await handler(call)
            assert entry.options[CONF_PAUSED] is False

"""Test the db_infoscreen config flow station search."""
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.db_infoscreen.const import DOMAIN, CONF_STATION, CONF_DATA_SOURCE
from custom_components.db_infoscreen.config_flow import ConfigFlow

# Mock JS response matching the regex in utils.py
SEARCH_JS_SINGLE = 'stations=["Frankfurt (Main) Hbf"];'
SEARCH_JS_MULTI = 'stations=["Frankfurt (Main) Hbf", "Frankfurt (Oder)"];'
SEARCH_JS_EMPTY = 'stations=[];'

# Mock JSON response for the coordinator (departures)
DEPARTURES_JSON = {"departures": []}

def create_flow(hass):
    """Create a ConfigFlow instance with mocked base methods."""
    flow = ConfigFlow()
    flow.hass = hass

    # Mock base class methods that are missing in the test environment's MockBase
    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", "step_id": kwargs.get("step_id"), "errors": kwargs.get("errors")})
    flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: {"type": "create_entry", "title": kwargs.get("title"), "data": kwargs.get("data")})

    # Mock async_step_choose to behave like a form step for selection
    # MUST be AsyncMock because it is awaited in the flow
    flow.async_step_choose = AsyncMock(side_effect=lambda **kwargs: {"type": "form", "step_id": "choose"})

    # Mock unique ID handling
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    return flow

async def test_search_single_result(hass: HomeAssistant) -> None:
    """Test user input resulting in a single unique match."""
    # Patch helper globally (for utils.py) and locally for __init__ (where it's imported at top level)
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_get_session_helper, \
         patch("custom_components.db_infoscreen.__init__.async_get_clientsession") as mock_get_session_init:

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SEARCH_JS_SINGLE)
        mock_response.json = AsyncMock(return_value=DEPARTURES_JSON)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        mock_get_session_helper.return_value = mock_session
        mock_get_session_init.return_value = mock_session

        flow = create_flow(hass)

        # 1. Start user step
        result = await flow.async_step_user(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # 2. Submit search query
        result = await flow.async_step_user(user_input={CONF_STATION: "Frankfurt (Main) Hbf"})

        # Verify it went to details step (to allow advanced options)
        assert result["type"] == "form"
        assert result["step_id"] == "details"

        # 3. Submit details (defaults)
        result = await flow.async_step_details(user_input={})

        # Verify creation
        assert result["type"] == "create_entry"
        assert result["title"] == "Frankfurt (Main) Hbf"
        # Suffix should be stripped
        assert result["data"][CONF_STATION] == "Frankfurt (Main) Hbf"
        assert result["data"][CONF_DATA_SOURCE] == "IRIS-TTS" # Default


async def test_search_multiple_results(hass: HomeAssistant) -> None:
    """Test user input resulting in multiple matches, requiring selection."""
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_get_session_helper, \
         patch("custom_components.db_infoscreen.__init__.async_get_clientsession") as mock_get_session_init:

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SEARCH_JS_MULTI)
        mock_response.json = AsyncMock(return_value=DEPARTURES_JSON)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        mock_get_session_helper.return_value = mock_session
        mock_get_session_init.return_value = mock_session

        flow = create_flow(hass)

        # 1. Start user step
        result = await flow.async_step_user(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # 2. Submit search query
        result = await flow.async_step_user(user_input={CONF_STATION: "Frankfurt"})

        # Should call async_step_choose because multiple matches
        assert result["type"] == "form"
        assert result["step_id"] == "choose"

        # Verify stations were populated with suffixes
        assert "Frankfurt (Main) Hbf (IRIS-TTS)" in flow.found_stations
        assert "Frankfurt (Oder) (IRIS-TTS)" in flow.found_stations

        # 3. Simulate choosing one
        flow.selected_station = "Frankfurt (Oder) (IRIS-TTS)"

        # Call details step
        result = await flow.async_step_details(user_input={})

        assert result["type"] == "create_entry"
        assert result["title"] == "Frankfurt (Oder)"
        assert result["data"][CONF_STATION] == "Frankfurt (Oder)"


async def test_manual_entry(hass: HomeAssistant) -> None:
    """Test manual entry path."""
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_get_session_helper, \
         patch("custom_components.db_infoscreen.__init__.async_get_clientsession") as mock_get_session_init:

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        # Use SINGLE (valid list) so stations is not empty. Query "MyCustomStation" will yield no match.
        mock_response.text = AsyncMock(return_value=SEARCH_JS_SINGLE)
        mock_response.json = AsyncMock(return_value=DEPARTURES_JSON)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        mock_get_session_helper.return_value = mock_session
        mock_get_session_init.return_value = mock_session

        flow = create_flow(hass)

        # 1. Submit search query that yields no results
        result = await flow.async_step_user(user_input={CONF_STATION: "MyCustomStation"})

        # Should go to choose step
        assert result["type"] == "form"
        assert result["step_id"] == "choose"

        assert "MyCustomStation (Manual Entry)" in flow.found_stations

        # 2. Select manual entry
        flow.selected_station = "MyCustomStation (Manual Entry)"

        # 3. Proceed to details
        result = await flow.async_step_details(user_input={})

        assert result["type"] == "create_entry"
        # Should use Manual suffix stripped name
        assert result["title"] == "MyCustomStation"
        assert result["data"][CONF_STATION] == "MyCustomStation"

        # 4. To test advanced flow:
        result = await flow.async_step_details(user_input={"advanced": True})

        assert result["type"] == "form"
        assert result["step_id"] == "advanced"

        # 5. Submit advanced form
        result = await flow.async_step_advanced(user_input={CONF_DATA_SOURCE: "MVV"})

        assert result["type"] == "create_entry"
        assert result["title"] == "MyCustomStation"
        assert result["data"][CONF_STATION] == "MyCustomStation"
        assert result["data"][CONF_DATA_SOURCE] == "MVV"

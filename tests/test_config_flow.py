from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from custom_components.db_infoscreen.config_flow import ConfigFlow
from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_DATA_SOURCE,
    CONF_NEXT_DEPARTURES,
    CONF_SERVER_TYPE,
    SERVER_TYPE_OFFICIAL,
)

from homeassistant.data_entry_flow import FlowResultType
from homeassistant import config_entries


@pytest.mark.asyncio
async def test_form_user(hass):
    """Test we get the form."""
    # Set up mock response
    hass.config_entries.flow.async_init.return_value = {
        "type": FlowResultType.FORM,
        "step_id": "user",
        "errors": {},
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_form_create_entry(hass):
    """Test that validating the user input works and creates an entry (multi-step)."""
    # Initialize the flow
    flow = ConfigFlow()
    flow.hass = hass

    # Mock show_form
    flow.async_show_form = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
        }
    )

    # 0. Server Step
    with patch(
        "custom_components.db_infoscreen.utils.async_verify_server", return_value=True
    ):
        result1 = await flow.async_step_user({CONF_SERVER_TYPE: SERVER_TYPE_OFFICIAL})
    assert result1["type"] == FlowResultType.FORM
    assert result1["step_id"] == "station_search"

    # 1. Search Step
    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["München Hbf"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=["München Hbf"],
    ):
        # The search query is now processed by async_step_station_search
        result2 = await flow.async_step_station_search({CONF_STATION: "München Hbf"})

    assert result2["type"] == FlowResultType.FORM
    assert flow.selected_station == "München Hbf (IRIS-TTS)"

    # 2. Details Step
    with patch(
        "custom_components.db_infoscreen.config_flow.ConfigFlow._async_create_db_entry",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {
            "type": FlowResultType.CREATE_ENTRY,
            "title": "München Hbf",
        }
        result3 = await flow.async_step_details(
            {
                CONF_DATA_SOURCE: "IRIS-TTS",
            }
        )

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_form_create_entry_advanced(hass):
    """Test that validating advanced user input works, including excluded_directions."""
    from custom_components.db_infoscreen.const import CONF_EXCLUDED_DIRECTIONS

    flow = ConfigFlow()
    flow.hass = hass
    flow.selected_station = "Stuttgart Hbf"

    flow.async_show_form = MagicMock(  # type: ignore[method-assign]
        return_value={"type": FlowResultType.FORM, "step_id": "advanced"}
    )

    # 2. Details Step with advanced=True
    result_details = await flow.async_step_details(
        {CONF_DATA_SOURCE: "IRIS-TTS", "advanced": True}
    )

    assert result_details["type"] == FlowResultType.FORM
    assert result_details["step_id"] == "advanced"

    # 3. Advanced Step passing excluded_directions
    with patch(
        "custom_components.db_infoscreen.config_flow.ConfigFlow._async_create_db_entry",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Stuttgart Hbf",
        }

        result_advanced = await flow.async_step_advanced(
            {
                CONF_EXCLUDED_DIRECTIONS: "Berlin",
            }
        )

    assert result_advanced["type"] == FlowResultType.CREATE_ENTRY
    mock_create.assert_called_once()
    args, kwargs = mock_create.call_args
    # Verify our basic options + advanced options combine properly:
    assert args[0][CONF_EXCLUDED_DIRECTIONS] == "Berlin"
    assert args[0][CONF_DATA_SOURCE] == "IRIS-TTS"
    assert "advanced" not in args[0]


@pytest.mark.asyncio
async def test_form_multiple_matches(hass):
    """Test the flow when multiple station matches are found."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.async_show_form = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
        }
    )

    # Server selection first
    with patch(
        "custom_components.db_infoscreen.utils.async_verify_server", return_value=True
    ):
        await flow.async_step_user({CONF_SERVER_TYPE: SERVER_TYPE_OFFICIAL})

    # Search for something ambiguous
    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["München Hbf", "München Ost"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=["München Hbf", "München Ost"],
    ):

        result2 = await flow.async_step_station_search({CONF_STATION: "München"})

    assert result2["type"] == FlowResultType.FORM
    assert flow.found_stations == [
        "München Hbf (IRIS-TTS)",
        "München Ost (IRIS-TTS)",
        "München (Manual Entry)",
    ]


@pytest.mark.asyncio
async def test_form_no_matches_manual_override(hass):
    """Test manual entry override when no matches found."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.async_show_form = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
        }
    )

    # Server selection
    with patch(
        "custom_components.db_infoscreen.utils.async_verify_server", return_value=True
    ):
        await flow.async_step_user({CONF_SERVER_TYPE: SERVER_TYPE_OFFICIAL})

    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["Berlin Hbf"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=[],
    ):

        result2 = await flow.async_step_station_search(
            {CONF_STATION: "MyCustomStation"}
        )

    assert result2["type"] == FlowResultType.FORM
    assert flow.found_stations == ["MyCustomStation (Manual Entry)"]
    assert flow.no_match is True


@pytest.mark.asyncio
async def test_options_flow(hass):
    """Test options flow menu."""
    from custom_components.db_infoscreen.config_flow import OptionsFlowHandler

    entry = MagicMock()
    entry.data = {CONF_STATION: "München Hbf"}
    entry.options = {CONF_NEXT_DEPARTURES: 5}

    flow = OptionsFlowHandler(entry)
    flow.async_show_menu = MagicMock(  # type: ignore[method-assign]
        return_value={"type": FlowResultType.MENU, "step_id": "init"}
    )

    result = await flow.async_step_init()
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_form_unreachable_servers(hass):
    """Test error keys returned when official or FaserF servers are unreachable."""
    from custom_components.db_infoscreen.const import SERVER_TYPE_FASERF

    flow = ConfigFlow()
    flow.hass = hass

    # Mock show_form
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
            "errors": kwargs.get("errors"),
        }
    )

    # Test Official Server Unreachable
    with patch(
        "custom_components.db_infoscreen.utils.async_verify_server", return_value=False
    ):
        result = await flow.async_step_user({CONF_SERVER_TYPE: SERVER_TYPE_OFFICIAL})
    assert result["errors"] == {"base": "cannot_connect_official"}

    # Test FaserF Server Unreachable
    with patch(
        "custom_components.db_infoscreen.utils.async_verify_server", return_value=False
    ):
        result = await flow.async_step_user({CONF_SERVER_TYPE: SERVER_TYPE_FASERF})
    assert result["errors"] == {"base": "cannot_connect_faserf"}


@pytest.mark.asyncio
async def test_hassio_discovery_already_installed(hass):
    """Test Hass.io discovery flow when addon is already installed."""
    flow = ConfigFlow()
    flow.hass = hass

    # Mock show_form
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
        }
    )

    addon_info = MagicMock()
    mock_addon_manager = AsyncMock()
    mock_addon_manager.async_get_addon_info.return_value = addon_info

    with patch(
        "homeassistant.components.hassio.is_hassio", return_value=True, create=True
    ), patch.object(
        flow, "_async_get_addon_manager", return_value=mock_addon_manager
    ), patch(
        "homeassistant.components.hassio.AddonState", create=True
    ) as mock_state, patch.object(
        flow, "_async_prefill_addon_info", new_callable=AsyncMock
    ) as mock_prefill:

        mock_state.NOT_INSTALLED = "not_installed"
        addon_info.state = "installed"
        flow.context = {}

        result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    mock_prefill.assert_called_once()


@pytest.mark.asyncio
async def test_hassio_discovery_not_installed(hass):
    """Test Hass.io discovery flow when addon is not installed."""
    flow = ConfigFlow()
    flow.hass = hass

    # Mock show_form
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {
            "type": FlowResultType.FORM,
            "step_id": kwargs.get("step_id"),
        }
    )

    addon_info = MagicMock()
    mock_addon_manager = AsyncMock()
    mock_addon_manager.async_get_addon_info.return_value = addon_info

    with patch(
        "homeassistant.components.hassio.is_hassio", return_value=True, create=True
    ), patch.object(
        flow, "_async_get_addon_manager", return_value=mock_addon_manager
    ), patch(
        "homeassistant.components.hassio.AddonState", create=True
    ) as mock_state:

        mock_state.NOT_INSTALLED = "not_installed"
        addon_info.state = "not_installed"
        flow.context = {}

        result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "hassio_confirm"




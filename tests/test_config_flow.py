from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from custom_components.db_infoscreen.config_flow import ConfigFlow
from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_DATA_SOURCE,
    CONF_NEXT_DEPARTURES,
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
    flow.async_show_form = MagicMock(
        return_value={"type": FlowResultType.FORM, "step_id": "details"}
    )

    # 1. Search Step
    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["München Hbf"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=["München Hbf"],
    ):

        # We call the method directly on the class instance since we mocked the modules
        result2 = await flow.async_step_user({CONF_STATION: "München Hbf"})

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
async def test_form_multiple_matches(hass):
    """Test the flow when multiple station matches are found."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.async_show_form = MagicMock(
        return_value={"type": FlowResultType.FORM, "step_id": "choose"}
    )

    # Search for something ambiguous
    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["München Hbf", "München Ost"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=["München Hbf", "München Ost"],
    ):

        result2 = await flow.async_step_user({CONF_STATION: "München"})

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
    flow.async_show_form = MagicMock(
        return_value={"type": FlowResultType.FORM, "step_id": "choose"}
    )

    with patch(
        "custom_components.db_infoscreen.config_flow.async_get_stations",
        return_value=["Berlin Hbf"],
    ), patch(
        "custom_components.db_infoscreen.config_flow.find_station_matches",
        return_value=[],
    ):

        result2 = await flow.async_step_user({CONF_STATION: "MyCustomStation"})

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
    flow.async_show_menu = MagicMock(
        return_value={"type": FlowResultType.MENU, "step_id": "init"}
    )

    result = await flow.async_step_init()
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

"""Test the DB Infoscreen config flow."""

from unittest.mock import patch
import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_DATA_SOURCE,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES,
    CONF_ENABLE_TEXT_VIEW,
    CONF_VIA_STATIONS,
    CONF_DIRECTION,
    CONF_PLATFORMS,
)


@pytest.mark.asyncio
async def test_form_user(hass):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_form_create_entry(hass):
    """Test that validating the user input works and creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.db_infoscreen.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION: "München Hbf",
                CONF_DATA_SOURCE: "IRIS-TTS",
                CONF_VIA_STATIONS: "Pasing",
                CONF_DIRECTION: "München-Pasing",
                CONF_PLATFORMS: "1,2",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert (
        result2["title"]
        == "München Hbf platform 1,2 via Pasing direction München-Pasing"
    )
    assert result2["data"][CONF_STATION] == "München Hbf"
    assert "Pasing" in result2["data"][CONF_VIA_STATIONS]
    assert result2["data"][CONF_DIRECTION] == "München-Pasing"
    assert result2["data"][CONF_PLATFORMS] == "1,2"
    assert mock_setup_entry.called


@pytest.mark.asyncio
async def test_form_duplicate_entry(hass, config_entry):
    """Test we check for duplicate entries."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STATION: "München Hbf",
            CONF_DATA_SOURCE: "IRIS-TTS",
        },
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_options_flow(hass, config_entry):
    """Test options flow menu."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "general_options" in result["menu_options"]
    assert "filter_options" in result["menu_options"]
    assert "display_options" in result["menu_options"]
    assert "advanced_options" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_general(hass, config_entry):
    """Test general options."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Select General
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "general_options"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "general_options"

    # Save
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {CONF_NEXT_DEPARTURES: 10, CONF_UPDATE_INTERVAL: 5},
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_NEXT_DEPARTURES] == 10
    assert result3["data"][CONF_UPDATE_INTERVAL] == 5


@pytest.mark.asyncio
async def test_options_flow_display(hass, config_entry):
    """Test display options inc. enable_text_view."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Select Display
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "display_options"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "display_options"

    # Save
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {CONF_ENABLE_TEXT_VIEW: True},
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"][CONF_ENABLE_TEXT_VIEW] is True


@pytest.mark.asyncio
async def test_options_flow_filter_and_advanced(hass, config_entry):
    """Test filter and advanced options to ensure no 500 errors."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Select Filter
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "filter_options"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "filter_options"

    # Save Filter (update some values)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {"platforms": "1, 2"},
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["data"]["platforms"] == "1, 2"

    # Verify Advanced Options load correctly
    result4 = await hass.config_entries.options.async_init(config_entry.entry_id)
    result5 = await hass.config_entries.options.async_configure(
        result4["flow_id"],
        {"next_step_id": "advanced_options"},
    )
    assert result5["type"] == FlowResultType.FORM
    assert result5["step_id"] == "advanced_options"

    # Save Advanced
    result6 = await hass.config_entries.options.async_configure(
        result5["flow_id"],
        {"custom_api_url": "http://localhost"},
    )
    assert result6["type"] == FlowResultType.CREATE_ENTRY
    assert result6["data"]["custom_api_url"] == "http://localhost"


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="München Hbf",
        data={
            CONF_STATION: "München Hbf",
            CONF_DATA_SOURCE: "IRIS-TTS",
        },
        options={
            CONF_NEXT_DEPARTURES: DEFAULT_NEXT_DEPARTURES,
        },
    )

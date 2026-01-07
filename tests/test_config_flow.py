"""Test the DB Infoscreen config flow."""

from unittest.mock import patch
import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_DATA_SOURCE,
    CONF_NEXT_DEPARTURES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NEXT_DEPARTURES,
    CONF_ENABLE_TEXT_VIEW,
)


async def test_form_user(hass):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


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
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "München Hbf"
    assert result2["data"][CONF_STATION] == "München Hbf"
    assert result2["data"][CONF_DATA_SOURCE] == "IRIS-TTS"
    assert mock_setup_entry.called


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


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    return config_entries.MockConfigEntry(
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

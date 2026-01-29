"""Test the comprehensive options flow."""

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.db_infoscreen.const import (
    DOMAIN,
    CONF_STATION,
    CONF_DATA_SOURCE,
    CONF_VIA_STATIONS,
    CONF_PLATFORMS,
    CONF_UPDATE_INTERVAL,
)


@pytest.mark.asyncio
async def test_full_options_lifecycle(hass):
    """Test a full lifecycle of editing multiple option pages."""
    # 1. Setup initial entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="München Hbf",
        data={
            CONF_STATION: "München Hbf",
            CONF_DATA_SOURCE: "IRIS-TTS",
            CONF_VIA_STATIONS: ["Pasing", "Laim"],  # Initial via stations
            CONF_PLATFORMS: "1,2",
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    # 2. Initialize Options Flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    # 3. Edit General Options
    result_gen = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "general_options"},
    )
    assert result_gen["step_id"] == "general_options"

    result_save_gen = await hass.config_entries.options.async_configure(
        result_gen["flow_id"],
        {CONF_UPDATE_INTERVAL: 10},
    )
    assert result_save_gen["type"] == FlowResultType.CREATE_ENTRY

    # Verify persistence: options should now have update_interval,
    # but theoretically NOT via_stations (as they are in data).
    # But wait, our logic uses merged view.
    assert config_entry.options[CONF_UPDATE_INTERVAL] == 10

    # 4. Edit Filter Options
    # We need to restart the flow effectively for a new edit session usually,
    # but in test we can just call async_init again.
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result_filter = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "filter_options"},
    )

    # Verify Pre-filled values (Should come from DATA if likely undefined in options)
    # The form description isn't easily accessible here as a dict of values,
    # but we can assume the defaults were populated correctly if the code works.

    # Let's change Via Stations.
    # Important: The Code splits by PIPE '|' currently, but user might expect COMMA.
    # Let's test the current behavior first.

    result_save_filter = await hass.config_entries.options.async_configure(
        result_filter["flow_id"],
        {
            CONF_VIA_STATIONS: "Augsburg, Ulm",  # Using Comma as expected
            CONF_PLATFORMS: "5,6",
        },
    )
    assert result_save_filter["type"] == FlowResultType.CREATE_ENTRY

    # Verify persistence
    assert config_entry.options[CONF_UPDATE_INTERVAL] == 10  # Should still be there
    assert config_entry.options[CONF_PLATFORMS] == "5,6"
    assert config_entry.options[CONF_VIA_STATIONS] == ["Augsburg", "Ulm"]

    # 5. Verify Fallback logic
    # If we reset options, it should fall back to data
    config_entry.options = {}
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result_filter = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "filter_options"},
    )
    # We can't verify the default value directly in result object easily here
    # but we can dry-run submit
    result_save_default = await hass.config_entries.options.async_configure(
        result_filter["flow_id"],
        {},
    )
    # merged data should equal original data
    assert result_save_default["data"][CONF_VIA_STATIONS] == ["Pasing", "Laim"]


@pytest.mark.asyncio
async def test_via_station_delimiter_mismatch(hass):
    """Test to demonstrate potential confusion with delimiters."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, unique_id="Test", data={CONF_STATION: "Test"}, options={}
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result_filter = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "filter_options"},
    )

    # User enters comma separated list (as per UI label)
    result_save = await hass.config_entries.options.async_configure(
        result_filter["flow_id"],
        {CONF_VIA_STATIONS: "A, B"},
    )

    # Current code expects PIPE, so "A, B" becomes ONE element ["A, B"]
    # If this test asserts len == 2, it fails -> proving the bug/usability issue.
    via_list = result_save["data"][CONF_VIA_STATIONS]

    # We expect this to fail if we want Comma separation, but pass if we stick to Pipe.
    # The user request implies "fix errors", so this IS an error.
    # We asserting for what we WANT (Comma separation should work).
    # so we expect len(via_list) == 2.
    assert len(via_list) == 2, f"Expected 2 stations, got {via_list}"
    assert "A" in via_list
    assert "B" in via_list

"""Test the db_infoscreen config flow station search."""

from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.db_infoscreen.const import DOMAIN, CONF_STATION, CONF_DATA_SOURCE

SEARCH_XML_SINGLE = """<stations>
<station name="Frankfurt (Main) Hbf" ds100="FF" eva="8000105"/>
</stations>"""

SEARCH_XML_MULTI = """<stations>
<station name="Frankfurt (Main) Hbf" ds100="FF" eva="8000105"/>
<station name="Frankfurt (Oder)" ds100="BFF" eva="8010113"/>
</stations>"""

SEARCH_XML_EMPTY = """<stations></stations>"""


async def test_search_single_result(hass: HomeAssistant) -> None:
    """Test user input resulting in a single search result (auto-select)."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SEARCH_XML_SINGLE)
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION: "Frankfurt",
                CONF_DATA_SOURCE: "IRIS-TTS",
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Frankfurt (Main) Hbf"
        assert result["data"][CONF_STATION] == "Frankfurt (Main) Hbf"


async def test_search_multiple_results(hass: HomeAssistant) -> None:
    """Test user input resulting in multiple search results (selection step)."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SEARCH_XML_MULTI)
        mock_get.return_value.__aenter__.return_value = mock_response

        # 1. User Step
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION: "Frankfurt",
                CONF_DATA_SOURCE: "IRIS-TTS",
            },
        )

        # 2. Select Station Step
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "select_station"

        # Verify result contains dropdown
        assert CONF_STATION in result["data_schema"].schema

        # 3. Select one
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION: "Frankfurt (Oder)",
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Frankfurt (Oder)"
        assert result["data"][CONF_STATION] == "Frankfurt (Oder)"


async def test_search_no_results(hass: HomeAssistant) -> None:
    """Test user input with no results."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SEARCH_XML_EMPTY)
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_STATION: "NonExistentStationXYZ",
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "station_not_found"}

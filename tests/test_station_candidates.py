"""Tests for station candidate discovery in utils.py."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.db_infoscreen.utils import (
    async_get_station_candidates,
    parse_dbf_multiple_choices,
)


@pytest.mark.asyncio
async def test_async_get_station_candidates_json_success(hass: HomeAssistant) -> None:
    """Test successful station candidate fetching via JSON API."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 300
    mock_response.headers = {"Content-Type": "application/json"}

    # Mock json() as an async function
    async def json_side_effect():
        return {
            "candidates": [
                {"name": "Berlin Hbf", "code": "8011160"},
                {"name": "Berlin Zoologischer Garten", "code": "8010406"},
            ]
        }

    mock_response.json = MagicMock(side_effect=json_side_effect)

    # Mock text() as an async function to avoid returning MagicMocks
    async def text_side_effect():
        return ""

    mock_response.text = MagicMock(side_effect=text_side_effect)

    async def enter_side_effect():
        return mock_response

    mock_response.__aenter__ = MagicMock(side_effect=enter_side_effect)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.get.return_value = mock_response

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=mock_session,
    ):
        candidates = await async_get_station_candidates(
            hass, "http://localhost", "Berlin", "IRIS-TTS"
        )

        assert len(candidates) == 2
        assert candidates[0]["name"] == "Berlin Hbf"
        assert candidates[1]["code"] == "8010406"


@pytest.mark.asyncio
async def test_async_get_station_candidates_direct_match(hass: HomeAssistant) -> None:
    """Test direct station match (200 OK) via JSON API."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}

    # Mock json() for direct match
    async def json_side_effect():
        return {"departures": [], "station": {"name": "Berlin Hbf"}}

    mock_response.json = MagicMock(side_effect=json_side_effect)

    # Mock text()
    async def text_side_effect():
        return "Abfahrtstafel"

    mock_response.text = MagicMock(side_effect=text_side_effect)

    async def enter_side_effect():
        return mock_response

    mock_response.__aenter__ = MagicMock(side_effect=enter_side_effect)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session.get.return_value = mock_response

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=mock_session,
    ):
        candidates = await async_get_station_candidates(
            hass, "http://localhost", "Berlin Hbf", "IRIS-TTS"
        )

        assert len(candidates) == 1
        assert candidates[0]["name"] == "Berlin Hbf"


@pytest.mark.asyncio
async def test_async_get_station_candidates_html_fallback(hass: HomeAssistant) -> None:
    """Test fallback to HTML parsing when JSON fails or returns 300 with HTML."""
    mock_session = MagicMock()

    # Configure mocks using MagicMock + async side effects (most stable)
    def create_mock_response(
        status: int,
        content_type: str,
        text: str | None = None,
        json_data: dict | None = None,
        json_err: Exception | None = None,
    ) -> MagicMock:
        resp = MagicMock()
        resp.status = status
        resp.headers = {"Content-Type": content_type}

        async def text_func() -> str:
            return text or ""

        resp.text = MagicMock(side_effect=text_func)

        async def json_func() -> dict:
            if json_err:
                raise json_err
            return json_data or {}

        resp.json = MagicMock(side_effect=json_func)

        async def enter_func() -> MagicMock:
            return resp

        resp.__aenter__ = MagicMock(side_effect=enter_func)
        resp.__aexit__ = AsyncMock(return_value=None)
        return resp

    mock_json_response = create_mock_response(
        300, "application/json", json_err=Exception("Not JSON")
    )

    html_content = """
    <html>
        <body>
            <div class="error">Wählen Sie eine Station aus</div>
            <ul>
                <li><a href="/?station=8011160">Berlin Hbf</a></li>
                <li><a href="/Berlin%20Zoo?hafas=BVG">Berlin Zoo</a></li>
            </ul>
        </body>
    </html>
    """
    mock_html_response = create_mock_response(300, "text/html", text=html_content)

    # Configure mock session to return JSON then HTML
    mock_session.get.side_effect = [mock_json_response, mock_html_response]

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=mock_session,
    ):
        candidates = await async_get_station_candidates(
            hass, "http://localhost", "Berlin", "IRIS-TTS"
        )

        assert len(candidates) == 2
        assert candidates[0]["name"] == "Berlin Hbf"
        assert candidates[0]["code"] == "8011160"
        assert candidates[1]["name"] == "Berlin Zoo"
        assert candidates[1]["code"] == "Berlin Zoo"


def test_parse_dbf_multiple_choices_diverse_links() -> None:
    """Test extraction of station links from various HTML patterns including query-based and provider-specific ones."""
    html = """
    <ul>
        <li><a href="/?station=8000001">Station A (IRIS)</a></li>
        <li><a href="/Station%20B?hafas=BVG">Station B (HAFAS path)</a></li>
        <li><a href="/?station=MVV:1001&efa=MVV">Station C (EFA query)</a></li>
        <li><a href="/Station%20D?hafas=ÖBB&something=else">Station D (HAFAS extra params)</a></li>
        <li><a href="/_backend?hafas=1">Skip me (Backend)</a></li>
        <li><a href="https://finalrewind.org">Skip me (External)</a></li>
    </ul>
    """
    candidates = parse_dbf_multiple_choices(html)

    assert len(candidates) == 4
    assert candidates[0] == {"name": "Station A (IRIS)", "code": "8000001"}
    assert candidates[1] == {"name": "Station B (HAFAS path)", "code": "Station B"}
    assert candidates[2] == {"name": "Station C (EFA query)", "code": "MVV:1001"}
    assert candidates[3] == {
        "name": "Station D (HAFAS extra params)",
        "code": "Station D",
    }


def test_parse_dbf_multiple_choices_empty() -> None:
    """Test parsing with irrelevant content."""
    html = "<html><body><p>No stations here</p><a href='/_backend'>Settings</a></body></html>"
    candidates = parse_dbf_multiple_choices(html)
    assert candidates == []


@pytest.mark.asyncio
async def test_async_get_station_candidates_error(hass: HomeAssistant) -> None:
    """Test graceful failure when all lookups fail."""
    mock_session = MagicMock()
    mock_session.get.side_effect = Exception("Connection error")

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=mock_session,
    ):
        candidates = await async_get_station_candidates(
            hass, "http://localhost", "Unknown", "IRIS-TTS"
        )

        assert candidates == []

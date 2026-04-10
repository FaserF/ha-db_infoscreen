"""Tests for station candidate discovery in utils.py."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.db_infoscreen.utils import (
    async_get_station_candidates,
    parse_dbf_multiple_choices,
)


@pytest.mark.asyncio
async def test_async_get_station_candidates_json_success(hass):
    """Test successful station candidate fetching via JSON API."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 300
    mock_response.json.return_value = {
        "candidates": [
            {"name": "Berlin Hbf", "code": "8011160"},
            {"name": "Berlin Zoologischer Garten", "code": "8010406"},
        ]
    }

    mock_session.get.return_value.__aenter__.return_value = mock_response

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
async def test_async_get_station_candidates_direct_match(hass):
    """Test direct station match (200 OK) via JSON API."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_session.get.return_value.__aenter__.return_value = mock_response

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
async def test_async_get_station_candidates_html_fallback(hass):
    """Test fallback to HTML parsing when JSON fails or returns 300 with HTML."""
    mock_session = MagicMock()

    # First response (JSON) fails with 300 but no JSON body
    mock_json_response = AsyncMock()
    mock_json_response.status = 300
    mock_json_response.json.side_effect = Exception("Not JSON")

    # Second response (HTML)
    mock_html_response = AsyncMock()
    mock_html_response.status = 300
    mock_html_response.text.return_value = """
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

    # Configure mock session to return JSON then HTML
    mock_session.get.return_value.__aenter__.side_effect = [
        mock_json_response,
        mock_html_response,
    ]

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


def test_parse_dbf_multiple_choices_diverse_links():
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


def test_parse_dbf_multiple_choices_empty():
    """Test parsing with irrelevant content."""
    html = "<html><body><p>No stations here</p><a href='/_backend'>Settings</a></body></html>"
    candidates = parse_dbf_multiple_choices(html)
    assert candidates == []


@pytest.mark.asyncio
async def test_async_get_station_candidates_error(hass):
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

from __future__ import annotations

import logging
import json
import re
import difflib
import asyncio
import async_timeout
from urllib.parse import quote, unquote
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STATION_AUTOCOMPLETE_PATH = "/dyn/v110/autocomplete.js"
CACHE_KEY_DATA = "db_infoscreen_stations"
CACHE_KEY_UPDATE = "db_infoscreen_stations_last_update"
CACHE_DURATION = timedelta(hours=24)


def parse_datetime_flexible(value: Any, now: datetime) -> datetime | None:
    """
    Parse a datetime from various formats (timestamp, ISO, HH:MM).
    Standardizes parsing logic used across the integration.
    """
    from homeassistant.util import dt as dt_util

    if not value:
        return None

    try:
        # 1. Numeric timestamp
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.isdigit()
        ):
            return dt_util.utc_from_timestamp(int(value)).astimezone(now.tzinfo)

        # 2. ISO format or similar via HA helper
        parsed_dt = dt_util.parse_datetime(str(value))
        if parsed_dt:
            if parsed_dt.tzinfo is None:
                # If no date part was in the string (unlikely for parse_datetime, but safe)
                # or if we need to ensure local timezone
                return parsed_dt.replace(tzinfo=now.tzinfo)
            return parsed_dt.astimezone(now.tzinfo)

        # 3. Fallback for HH:MM format
        if isinstance(value, str) and ":" in value:
            parts = value.split(":")
            if len(parts) >= 2:
                try:
                    hour, minute = int(parts[0]), int(parts[1])
                    parsed_dt = now.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0,
                    )
                    # If the parsed time is significantly in the past, it's likely tomorrow
                    if parsed_dt < now - timedelta(hours=12):
                        parsed_dt += timedelta(days=1)
                    # If it's significantly in the future (e.g. 23:00 vs 01:00), it's likely yesterday
                    elif parsed_dt > now + timedelta(hours=12):
                        parsed_dt -= timedelta(days=1)
                    return parsed_dt
                except ValueError:
                    pass

    except (ValueError, TypeError):
        pass

    return None


def prune_response_cache(cache: dict, ttl: timedelta) -> None:
    """Remove expired entries from the global response cache."""
    from homeassistant.util import dt as dt_util

    now = dt_util.now().timestamp()
    expired = [
        url
        for url, (ts, _) in cache.items()
        if now - ts.timestamp() > ttl.total_seconds() + 3600  # Keep an hour buffer
    ]
    for url in expired:
        cache.pop(url, None)


def simple_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    from datetime import datetime, timedelta

    if isinstance(obj, (datetime, timedelta)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


async def async_verify_server(hass: HomeAssistant, base_url: str) -> bool:
    """Verify that a server is reachable and specifically a DBF instance."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    station_url = f"{base_url}{STATION_AUTOCOMPLETE_PATH}"
    _LOGGER.debug("Verifying server at %s", station_url)

    # Use a realistic User-Agent to avoid being blocked by simple scrapers/rate-limiters
    headers = {
        "User-Agent": "HomeAssistant-DBInfoScreen/2.0 (+https://github.com/FaserF/ha-db_infoscreen)"
    }

    try:
        session = async_get_clientsession(hass)
        # Bumping timeout to 12s for the official server which can be slow
        async with async_timeout.timeout(12):
            async with session.get(station_url, headers=headers) as response:
                # We expect 200 and some content containing 'stations='
                _LOGGER.debug(
                    "Verification response status for %s: %s", base_url, response.status
                )
                if response.status == 200:
                    content = await response.text()
                    is_valid = "stations=[" in content
                    if not is_valid:
                        _LOGGER.warning(
                            "Server at %s returned 200 but content did not look like a DBF instance",
                            base_url,
                        )
                    return is_valid

                _LOGGER.warning(
                    "Server at %s returned status %s", base_url, response.status
                )
                return False
    except asyncio.TimeoutError:
        _LOGGER.warning("Server verification timed out for %s (12s limit)", base_url)
        return False
    except Exception as e:
        _LOGGER.warning("Server verification failed for %s: %s", base_url, e)
        return False


async def async_get_stations(hass: HomeAssistant, base_url: str) -> list[str]:
    """
    Download and parse the station list from DBF.
    Check hass.data for cached list first.
    Refreshes cache if older than 24 hours.
    """
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    now = datetime.now(timezone.utc)
    station_url = f"{base_url}{STATION_AUTOCOMPLETE_PATH}"

    # Use a per-server cache key to avoid mixing stations from different providers
    server_slug = re.sub(r"[^a-zA-Z0-9]", "_", base_url)
    data_key = f"{CACHE_KEY_DATA}_{server_slug}"
    update_key = f"{CACHE_KEY_UPDATE}_{server_slug}"

    if data_key in hass.data and update_key in hass.data:
        last_update = hass.data[update_key]
        if now - last_update < CACHE_DURATION:
            _LOGGER.debug(
                "Using cached station list for %s (age: %s)",
                base_url,
                now - last_update,
            )
            return hass.data[data_key]

    _LOGGER.debug("Downloading station list from %s", station_url)
    try:
        session = async_get_clientsession(hass)
        async with async_timeout.timeout(10):
            async with session.get(station_url) as response:
                response.raise_for_status()
                content = await response.text()

                # Parse the JS content to extract the array
                match = re.search(r"stations=\[(.*?)\];", content, re.DOTALL)
                if match:
                    json_str = f"[{match.group(1)}]"
                    stations = json.loads(json_str)
                    hass.data[data_key] = stations
                    hass.data[update_key] = now
                    _LOGGER.debug("Parsed and cached %d stations", len(stations))
                    return stations
                else:
                    _LOGGER.error(
                        "Could not find station array in response from %s", base_url
                    )
                    if data_key in hass.data:
                        return hass.data[data_key]
                    return []
    except Exception as e:
        _LOGGER.error("Error downloading station list from %s: %s", base_url, e)
        if data_key in hass.data:
            return hass.data[data_key]
        return []


def find_station_matches(stations, query):
    """
    Find matches for the query in the station list.
    Returns a list of matching station names.
    Priority: Exact -> StartsWith -> Contains -> Fuzzy
    """
    if not query or not stations:
        return []

    query_lower = query.lower()

    # 1. Exact match (case-insensitive)
    exact = [s for s in stations if s.lower() == query_lower]
    if exact:
        return exact

    # 2. Starts with (case-insensitive)
    starts_with = [s for s in stations if s.lower().startswith(query_lower)]
    # If we have a good amount of "starts with" matches, return them.
    if starts_with:
        # Limit to 10 to avoid overwhelming the user
        return starts_with[:10]

    # 3. Contains (case-insensitive) - strictly stronger than fuzzy, but weaker than starts_with
    contains = [s for s in stations if query_lower in s.lower()]
    if contains:
        return contains[:10]

    # 4. Fuzzy match
    # cutoff=0.6 is a reasonable default for difflib
    # Use case-normalized fuzzy matching

    # Create a map of lower->original for O(1) lookup
    lower_map = {s.lower(): s for s in stations}

    fuzzy = difflib.get_close_matches(
        query_lower, list(lower_map.keys()), n=10, cutoff=0.6
    )
    # Map back to original casing
    if fuzzy:
        result = [lower_map[match] for match in fuzzy]
        return result
    return []


async def async_get_station_candidates(
    hass: HomeAssistant, server_url: str, station: str, source: str = "IRIS-TTS"
) -> list[dict[str, str]]:
    """Fetch station candidates from DBF backend."""
    from .const import DATA_SOURCE_MAP

    source_param = DATA_SOURCE_MAP.get(source, source)
    if source == "IRIS-TTS":
        source_param = ""  # Default is IRIS

    encoded_station = quote(station)

    # We try different lookup patterns to ensure compatibility
    lookups = [
        f"{server_url}/{encoded_station}.json?{source_param}{'&' if source_param else ''}mode=json",
        f"{server_url}/?station={encoded_station}&{source_param}{'&' if source_param else ''}mode=json",
        f"{server_url}/{encoded_station}?{source_param}",
        f"{server_url}/?station={encoded_station}&{source_param}",
    ]

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)

    for url in lookups:
        # Clean up double question marks or ampersands
        url = url.replace("??", "?").replace("?&", "?").replace("&&", "&").rstrip("?&")
        _LOGGER.debug("Trying candidate lookup: %s", url)

        try:
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    content_type = response.headers.get("Content-Type", "")

                    if "text/html" in content_type or response.status in [
                        200,
                        300,
                        500,
                    ]:
                        text = await response.text()

                        # Detect landing/home/search page (often shown when station not found)
                        if (
                            "inoffizieller Abfahrtsmonitor" in text
                            or "Oder hier eine Station angeben" in text
                        ):
                            # If it's the home page, but NOT a choice page, skip it
                            if not any(
                                x in text
                                for x in [
                                    "Wählen Sie",
                                    "Multiple Choice",
                                    "Mehrdeutige Eingabe",
                                ]
                            ):
                                _LOGGER.debug(
                                    "Detected landing page at %s, skipping", url
                                )
                                continue

                        # Detect Multiple Choice page - Broadened detection for localized/older versions
                        if (
                            any(
                                x in text
                                for x in [
                                    "Wählen Sie eine Station aus",
                                    "Multiple Choices",
                                    "Mehrdeutige Eingabe",
                                    "Bitte eine Station aus der Liste auswählen",
                                ]
                            )
                            or response.status == 300
                        ):
                            candidates = parse_dbf_multiple_choices(text)
                            if candidates:
                                return candidates

                        # If it's a 200 OK and looks like a real board
                        elif response.status == 200:
                            if any(
                                x in text
                                for x in [
                                    "Abfahrtstafel",
                                    "Abfahrten",
                                    "Display",
                                    "container",
                                ]
                            ):
                                return [{"name": station, "code": station}]

                    if (
                        "application/json" in content_type
                        or url.endswith(".json")
                        or "mode=json" in url
                    ):
                        try:
                            data = await response.json()
                            # Candidates in JSON
                            if "candidates" in data and data["candidates"]:
                                return [
                                    {"name": c["name"], "code": c["code"]}
                                    for c in data["candidates"]
                                ]

                            # Direct match JSON
                            if response.status == 200:
                                if (
                                    "departures" in data
                                    or "arrivals" in data
                                    or "station" in data
                                ):
                                    official_name = station
                                    if "station" in data and isinstance(
                                        data["station"], dict
                                    ):
                                        official_name = data["station"].get(
                                            "name", station
                                        )
                                    return [{"name": official_name, "code": station}]
                        except Exception:
                            # Re-check text if JSON fail just in case
                            pass

        except Exception as e:
            _LOGGER.debug("Lookup failed for %s: %s", url, e)

    return []


def parse_dbf_multiple_choices(html_text: str) -> list[dict[str, str]]:
    """Parse the HTML of a 300 Multiple Choices page from DBF."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_text, "html.parser")
    candidates = []

    for link in soup.find_all("a"):
        href_raw = link.get("href", "")
        if not isinstance(href_raw, str):
            continue
        href = href_raw
        name = link.text.strip()

        # Skip internal or obvious non-station links
        if not name or any(
            x in href for x in ["_backend", "_v110", "mode=json", "finalrewind.org"]
        ):
            continue

        # Pattern 1: /?station=CODE
        if "station=" in href:
            match = re.search(r"station=([^&?]+)", href)
            if match:
                code = unquote(match.group(1))
                candidates.append({"name": name, "code": code})
                continue

        # Pattern 2: /NAME?source=... (often used by EFA/HAFAS)
        if href.startswith("/") and any(
            param in href for param in ["hafas=", "efa=", "db="]
        ):
            # The part before '?' is usually the station ID/Name slug
            code = unquote(href.split("?", 1)[0].lstrip("/"))
            if code and code not in ["_autostop", "_backend", "search"]:
                candidates.append({"name": name, "code": code})
                continue

    # Pattern 3: <select name="input"> with <option> tags (used on user's server)
    for select in soup.find_all("select", attrs={"name": "input"}):
        for option in select.find_all("option"):
            # Cast to string to satisfy mypy (BeautifulSoup can return AttributeValueList or None)
            val = option.get("value", "")
            code = unquote(str(val))
            name = option.text.strip()
            if code and name:
                candidates.append({"name": name, "code": code})

    # Fallback to any <select> if name="input" wasn't found but candidates are still empty
    if not candidates:
        for option in soup.find_all("option"):
            # Cast to string to satisfy mypy
            val = option.get("value", "")
            code = unquote(str(val))
            name = option.text.strip()
            if (
                code
                and name
                and code not in ["app", "infoscreen", "multi", "single", "dep", "arr"]
            ):
                candidates.append({"name": name, "code": code})

    # Deduplicate by code
    seen = set()
    result = []
    for c in candidates:
        if c["code"] not in seen:
            result.append(c)
            seen.add(c["code"])

    return result

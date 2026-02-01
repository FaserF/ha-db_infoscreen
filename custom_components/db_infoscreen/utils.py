import logging
import json
import re
import difflib
import aiohttp
import async_timeout
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

STATION_URL = "https://dbf.finalrewind.org/dyn/v110/autocomplete.js"
CACHE_KEY_DATA = "db_infoscreen_stations"
CACHE_KEY_UPDATE = "db_infoscreen_stations_last_update"
CACHE_DURATION = timedelta(hours=24)


async def async_get_stations(hass):
    """
    Download and parse the station list from DBF.
    Check hass.data for cached list first.
    Refreshes cache if older than 24 hours.
    """
    now = datetime.now()

    if CACHE_KEY_DATA in hass.data and CACHE_KEY_UPDATE in hass.data:
        last_update = hass.data[CACHE_KEY_UPDATE]
        if now - last_update < CACHE_DURATION:
            _LOGGER.debug("Using cached station list (age: %s)", now - last_update)
            return hass.data[CACHE_KEY_DATA]
        else:
            _LOGGER.debug(
                "Cached station list expired (age: %s), refreshing...",
                now - last_update,
            )

    _LOGGER.debug("Downloading station list from %s", STATION_URL)
    try:
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(STATION_URL) as response:
                    response.raise_for_status()
                    content = await response.text()

                    # Parse the JS content to extract the array
                    match = re.search(r"stations=\[(.*?)\];", content, re.DOTALL)
                    if match:
                        json_str = f"[{match.group(1)}]"
                        stations = json.loads(json_str)
                        hass.data[CACHE_KEY_DATA] = stations
                        hass.data[CACHE_KEY_UPDATE] = now
                        _LOGGER.debug("Parsed and cached %d stations", len(stations))
                        return stations
                    else:
                        _LOGGER.error("Could not find station array in response")
                        # Return cached data if available even if expired, to be safe
                        if CACHE_KEY_DATA in hass.data:
                            _LOGGER.warning("Using expired cache due to parsing error.")
                            return hass.data[CACHE_KEY_DATA]
                        return []
    except Exception as e:
        _LOGGER.error("Error downloading station list: %s", e)
        # Fallback to expired cache if available
        if CACHE_KEY_DATA in hass.data:
            _LOGGER.warning("Using expired cache due to download error.")
            return hass.data[CACHE_KEY_DATA]
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
    fuzzy = difflib.get_close_matches(query, stations, n=10, cutoff=0.6)
    return fuzzy

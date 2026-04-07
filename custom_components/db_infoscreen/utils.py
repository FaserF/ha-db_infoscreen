import logging
import json
import re
import difflib
import async_timeout
from datetime import datetime, timedelta, timezone

_LOGGER = logging.getLogger(__name__)

STATION_AUTOCOMPLETE_PATH = "/dyn/v110/autocomplete.js"
CACHE_KEY_DATA = "db_infoscreen_stations"
CACHE_KEY_UPDATE = "db_infoscreen_stations_last_update"
CACHE_DURATION = timedelta(hours=24)


async def async_get_stations(hass, base_url: str):
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

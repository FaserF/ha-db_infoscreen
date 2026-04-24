from unittest.mock import MagicMock
import pytest
from datetime import datetime, timezone, timedelta
from custom_components.db_infoscreen.sensor import DBInfoScreenPunctualitySensor
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator
from homeassistant.util import dt as dt_util


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.departure_history = {}
    coord.config_entry = MagicMock()
    coord.config_entry.data = {}
    coord.config_entry.options = {}
    return coord


@pytest.fixture
def real_coordinator(hass):
    """Return a minimal real coordinator with departure_history for _update_history tests."""
    entry = MagicMock()
    entry.data = {
        "station": "test",
        "server_url": "http://localhost",
    }
    entry.options = {}
    entry.entry_id = "test_entry"
    coord = MagicMock(spec=DBInfoScreenCoordinator)
    coord.departure_history = {}
    coord.hass = hass
    # Bind the real method to this mock
    coord._update_history = DBInfoScreenCoordinator._update_history.__get__(coord)
    return coord


@pytest.mark.asyncio
async def test_punctuality_sensor_calculation(hass, mock_coordinator):
    """Test the statistics calculation logic."""
    now = dt_util.now()

    # 1. Setup history: 1 on-time, 1 delayed (10m), 1 cancelled
    mock_coordinator.departure_history = {
        "trip1": {
            "train": "ICE 1",
            "delay": 0,
            "is_cancelled": False,
            "timestamp": now,
        },
        "trip2": {
            "train": "ICE 2",
            "delay": 10,
            "is_cancelled": False,
            "timestamp": now,
        },
        "trip3": {"train": "ICE 3", "delay": 0, "is_cancelled": True, "timestamp": now},
    }

    sensor = DBInfoScreenPunctualitySensor(
        mock_coordinator, mock_coordinator.config_entry
    )

    stats = sensor._get_stats()

    # total=3, delayed=1, cancelled=1, on_time=1
    # punctuality = (1 / 3) * 100 = 33.3%
    assert stats["total_trains"] == 3
    assert stats["delayed_trains"] == 1
    assert stats["cancelled_trains"] == 1
    assert stats["punctuality_percent"] == 33.3

    # avg_delay = (0 + 10) / (3-1) = 5.0
    assert stats["average_delay"] == 5.0


@pytest.mark.asyncio
async def test_punctuality_sensor_empty(hass, mock_coordinator):
    """Test statistics when history is empty."""
    sensor = DBInfoScreenPunctualitySensor(
        mock_coordinator, mock_coordinator.config_entry
    )
    stats = sensor._get_stats()

    assert stats["total_trains"] == 0
    assert stats["punctuality_percent"] == 100.0


# ---------------------------------------------------------------------------
# Regression tests for issue #131 — AVV bus data producing 0 total_trains
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_history_avv_line_field(real_coordinator):
    """
    Regression: AVV buses use 'line' instead of 'train'.

    Before the fix, dep.get("train") returned None for every AVV entry,
    causing the `not train` guard to skip them all → departure_history stayed
    empty → punctuality reported 100% with 0 total_trains.
    """
    now_ts = int(datetime.now(timezone.utc).timestamp())
    departures = [
        {
            "line": "32",  # AVV field — no "train" key at all
            "trip_id": None,
            "departure_timestamp": now_ts,
            "delayDeparture": 0,
            "cancelled": False,
        },
        {
            "line": "36",
            "trip_id": None,
            "departure_timestamp": now_ts + 300,
            "delayDeparture": 8,  # > 5 min → delayed
            "cancelled": False,
        },
        {
            "line": "32",
            "trip_id": None,
            "departure_timestamp": now_ts + 600,
            "delayDeparture": 0,
            "isCancelled": True,  # raw API cancellation field
        },
    ]

    real_coordinator._update_history(departures)

    history = real_coordinator.departure_history
    assert (
        len(history) == 3
    ), f"Expected 3 entries, got {len(history)}: {list(history.keys())}"

    # Verify delay and cancellation were normalised correctly
    values = list(history.values())
    delays = sorted(v["delay"] for v in values)
    assert delays == [0, 0, 8]
    cancelled_count = sum(1 for v in values if v["is_cancelled"])
    assert cancelled_count == 1


@pytest.mark.asyncio
async def test_update_history_no_departure_timestamp(real_coordinator):
    """
    Regression: entries filtered early in the main loop never get
    departure_timestamp set.  Before the fix they all produced history key
    "<train>_None", collapsing into a single overwritten entry.

    The fix falls back to departure_datetime (set during pre-processing).
    """
    base = datetime.now(timezone.utc)
    departures = [
        {
            "train": "Bus 31",
            "trip_id": None,
            # No departure_timestamp (main loop was skipped)
            "departure_datetime": base,
            "delayDeparture": 0,
            "cancelled": False,
        },
        {
            "train": "Bus 31",
            "trip_id": None,
            "departure_datetime": base + timedelta(minutes=15),
            "delayDeparture": 0,
            "cancelled": False,
        },
        {
            "train": "Bus 31",
            "trip_id": None,
            "departure_datetime": base + timedelta(minutes=30),
            "delayDeparture": 7,
            "cancelled": False,
        },
    ]

    real_coordinator._update_history(departures)

    history = real_coordinator.departure_history
    # All three must be distinct keys — before the fix all would map to "Bus 31_None"
    assert len(history) == 3, (
        f"Expected 3 distinct history entries, got {len(history)}. "
        f"Keys: {list(history.keys())}"
    )


@pytest.mark.asyncio
async def test_update_history_raw_cancellation_fields(real_coordinator):
    """
    Regression: raw API cancellation field names (cancelled / isCancelled)
    must be recognised even when entries were filtered before the main loop's
    is_cancelled normalisation.
    """
    now_ts = int(datetime.now(timezone.utc).timestamp())
    departures = [
        {
            "train": "RE 1",
            "trip_id": None,
            "departure_timestamp": now_ts,
            "cancelled": True,  # raw HAFAS field
        },
        {
            "train": "RE 2",
            "trip_id": None,
            "departure_timestamp": now_ts + 300,
            "isCancelled": True,  # raw DBF field
        },
        {
            "train": "RE 3",
            "trip_id": None,
            "departure_timestamp": now_ts + 600,
            # no cancellation field → not cancelled
        },
    ]

    real_coordinator._update_history(departures)

    history = real_coordinator.departure_history
    assert len(history) == 3

    cancelled = [v for v in history.values() if v["is_cancelled"]]
    assert len(cancelled) == 2, f"Expected 2 cancelled, got {len(cancelled)}"

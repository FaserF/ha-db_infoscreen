import aiohttp
import pytest
import warnings
from unittest.mock import MagicMock, patch
from homeassistant.core import HomeAssistant
from custom_components.db_infoscreen.__init__ import DBInfoScreenCoordinator
from custom_components.db_infoscreen.sensor import (
    DBInfoSensor,
    DBInfoScreenWatchdogSensor,
    DBInfoScreenLeaveNowSensor,
)
from custom_components.db_infoscreen.binary_sensor import (
    DBInfoScreenElevatorBinarySensor,
    DBInfoScreenDelayBinarySensor,
    DBInfoScreenCancellationBinarySensor,
)
from custom_components.db_infoscreen.calendar import DBInfoScreenCalendar

# Make sure pytest-socket knows we need sockets for these tests
pytestmark = [pytest.mark.allow_sockets, pytest.mark.enable_socket]

original_allowed_hosts = None
original_allowed_hosts_saved = False


def _enable_socket_temporarily():
    """Bypass pytest-socket blocking during these tests."""
    global original_allowed_hosts, original_allowed_hosts_saved
    try:
        import pytest_socket

        pytest_socket.enable_socket()
        if not original_allowed_hosts_saved and hasattr(
            pytest_socket, "_allowed_hosts"
        ):
            original_allowed_hosts = pytest_socket._allowed_hosts
            original_allowed_hosts_saved = True
        pytest_socket.socket_allow_hosts(None)
    except (ImportError, AttributeError):
        pass
    try:
        # Also clean HASocketBlockedError instances from pytest-homeassistant-custom-component
        from pytest_homeassistant_custom_component.plugins import HASocketBlockedError

        HASocketBlockedError.instances.clear()
    except ImportError:
        pass


def _restore_socket_state():
    """Restore pytest-socket allow list to original state."""
    global original_allowed_hosts, original_allowed_hosts_saved
    if original_allowed_hosts_saved:
        try:
            import pytest_socket

            pytest_socket.socket_allow_hosts(original_allowed_hosts)
        except (ImportError, AttributeError):
            pass


@pytest.fixture(autouse=True)
def auto_enable_socket():
    """Automatically enable socket for every test in this module."""
    _enable_socket_temporarily()
    yield
    _restore_socket_state()


async def check_server_status() -> tuple[bool, str]:
    """Check if dbf.fabiseitz.de is reachable and returns valid data."""
    _enable_socket_temporarily()
    try:
        # Use a standard session with custom User-Agent to verify access
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            # Note: fetch without admode to avoid Cloudflare/proxy 502/530 errors
            async with session.get(
                "https://dbf.fabiseitz.de/M%C3%BCnchen%20Ost.json", timeout=5
            ) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        if "departures" in data:
                            return True, "Reachable and returns valid departures"
                        return False, f"Invalid JSON schema: {str(data)[:100]}"
                    except Exception as json_err:
                        return False, f"JSON parse error: {json_err}"
                return False, f"HTTP status {resp.status}"
    except Exception as conn_err:
        return False, f"Connection error: {conn_err}"


@pytest.fixture(name="live_coordinator")
async def live_coordinator_fixture(hass: HomeAssistant):
    """Fixture to provide a coordinator connected to the live API, or skip if down."""
    _enable_socket_temporarily()
    reachable, reason = await check_server_status()
    if not reachable:
        warnings.warn(
            UserWarning(
                f"Skipping live test: dbf.fabiseitz.de is not available ({reason})"
            )
        )
        pytest.skip(f"dbf.fabiseitz.de is not available ({reason})")

    # Clear any recorded HASocketBlockedError again
    try:
        from pytest_homeassistant_custom_component.plugins import HASocketBlockedError

        HASocketBlockedError.instances.clear()
    except ImportError:
        pass

    entry = MagicMock()
    entry.entry_id = "live_test_entry"
    entry.data = {"station": "München Ost"}
    entry.options = {
        "server_type": "custom",
        "server_url": "https://dbf.fabiseitz.de",
        "detailed": True,
    }
    entry.title = "München Ost"

    coordinator = DBInfoScreenCoordinator(hass, entry)

    # Use standard default URL for fetch to bypass the admode=dep which causes 502 on Cloudflare
    coordinator.fetch_url = "https://dbf.fabiseitz.de/M%C3%BCnchen%20Ost.json"
    coordinator.api_url = "https://dbf.fabiseitz.de/M%C3%BCnchen%20Ost.json"

    # We must patch async_get_clientsession to use a real aiohttp session and bypass Home Assistant network dependencies
    session = aiohttp.ClientSession()
    with (
        patch(
            "custom_components.db_infoscreen.__init__.async_get_clientsession",
            return_value=session,
        ),
        patch(
            "custom_components.db_infoscreen.__init__.repairs.clear_all_issues_for_entry"
        ),
    ):
        await coordinator.async_refresh()

    yield coordinator, entry
    await session.close()


@pytest.mark.asyncio
async def test_live_data_structure(live_coordinator) -> None:
    """Test that the live data contains required fields and station messages."""
    coordinator, entry = live_coordinator
    assert coordinator.last_update_success is True
    assert len(coordinator.data) > 0

    # Test that each departure has the normalized fields
    for dep in coordinator.data:
        assert "train" in dep
        assert "destination" in dep
        assert "departure_timestamp" in dep
        assert "is_cancelled" in dep
        assert "delay" in dep

    # Test message and elevator issues lists
    assert isinstance(coordinator.station_messages, list)
    assert isinstance(coordinator.raw_elevator_issues, list)


@pytest.mark.asyncio
async def test_live_filtering_options(hass: HomeAssistant, live_coordinator) -> None:
    """Test various filtering features against the live API response."""
    coordinator, entry = live_coordinator
    raw_data = coordinator.data
    if not raw_data:
        return

    # 1. Platform Filter
    sample_platform = raw_data[0].get("platform")
    if sample_platform:
        entry.options["platforms"] = str(sample_platform)
        filtered_coord = DBInfoScreenCoordinator(hass, entry)
        filtered_coord.fetch_url = "https://dbf.fabiseitz.de/M%C3%BCnchen%20Ost.json"
        # Force local filtering for testing
        filtered_coord._platforms_filtered_server_side = False

        session = aiohttp.ClientSession()
        with (
            patch(
                "custom_components.db_infoscreen.__init__.async_get_clientsession",
                return_value=session,
            ),
            patch(
                "custom_components.db_infoscreen.__init__.repairs.clear_all_issues_for_entry"
            ),
        ):
            await filtered_coord.async_refresh()
        await session.close()

        assert len(filtered_coord.data) > 0
        for dep in filtered_coord.data:
            assert str(dep.get("platform")) == str(sample_platform)

    # 2. Ignored Train Types Filter
    entry.options["ignored_train_types"] = ["S"]
    filtered_coord_train = DBInfoScreenCoordinator(hass, entry)
    filtered_coord_train.fetch_url = "https://dbf.fabiseitz.de/M%C3%BCnchen%20Ost.json"

    session = aiohttp.ClientSession()
    with (
        patch(
            "custom_components.db_infoscreen.__init__.async_get_clientsession",
            return_value=session,
        ),
        patch(
            "custom_components.db_infoscreen.__init__.repairs.clear_all_issues_for_entry"
        ),
    ):
        await filtered_coord_train.async_refresh()
    await session.close()

    for dep in filtered_coord_train.data:
        assert "s_bahn" not in dep.get("trainClasses", [])


@pytest.mark.asyncio
async def test_live_sensor_entities(hass: HomeAssistant, live_coordinator) -> None:
    """Test that sensor attributes and states map correctly with live data."""
    coordinator, entry = live_coordinator
    assert coordinator.last_update_success is True

    # DBInfoSensor
    sensor = DBInfoSensor(coordinator, entry, "München Ost", [], "", "", False)
    assert sensor.native_value is not None
    attrs = sensor.extra_state_attributes
    assert "station_messages" in attrs
    assert isinstance(attrs["station_messages"], list)

    # Watchdog Sensor
    watchdog = DBInfoScreenWatchdogSensor(coordinator, entry)
    assert watchdog.native_value is not None
    assert isinstance(watchdog.extra_state_attributes, dict)

    # Leave Now Sensor
    leave_now = DBInfoScreenLeaveNowSensor(coordinator, entry)
    assert leave_now.native_value is not None or leave_now.native_value == 0
    assert "walk_time" in leave_now.extra_state_attributes


@pytest.mark.asyncio
async def test_live_binary_sensors(hass: HomeAssistant, live_coordinator) -> None:
    """Test binary sensors attributes with live data."""
    coordinator, entry = live_coordinator
    assert coordinator.last_update_success is True

    # Elevator Sensor
    elevator = DBInfoScreenElevatorBinarySensor(coordinator, entry, None)
    attrs = elevator.extra_state_attributes
    assert "defective_facilities" in attrs
    for facility in attrs["defective_facilities"]:
        assert "facility_type" in facility
        assert "platform" in facility
        assert "text" in facility
        assert "status" in facility

    # Delay Sensor
    delay_sensor = DBInfoScreenDelayBinarySensor(coordinator, entry)
    assert isinstance(delay_sensor.is_on, bool)

    # Cancellation Sensor
    cancel_sensor = DBInfoScreenCancellationBinarySensor(coordinator, entry)
    assert isinstance(cancel_sensor.is_on, bool)


@pytest.mark.asyncio
async def test_live_calendar_events(hass: HomeAssistant, live_coordinator) -> None:
    """Test that calendar event generation matches live coordinator configuration."""
    coordinator, entry = live_coordinator
    assert coordinator.last_update_success is True

    calendar = DBInfoScreenCalendar(coordinator, entry)
    events = calendar._get_events_from_departures()
    assert isinstance(events, list)
    if events:
        event = events[0]
        assert event.summary is not None
        assert event.start is not None
        assert event.end is not None
        assert event.location is not None

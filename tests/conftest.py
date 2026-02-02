"""Global fixtures and mocks for db_infoscreen integration tests."""

import sys
import os
import types
from unittest.mock import MagicMock, AsyncMock
import pytest

# Try to import pytest-homeassistant-custom-component
import importlib.util

PYTEST_HA_AVAILABLE = (
    importlib.util.find_spec("pytest_homeassistant_custom_component") is not None
)

# Only mock if pytest-homeassistant-custom-component is not available
if not PYTEST_HA_AVAILABLE:
    # 1. Mock homeassistant before any component imports
    if "homeassistant" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        ha.__path__ = []
        sys.modules["homeassistant"] = ha

    # Mock homeassistant.components
    if "homeassistant.components" not in sys.modules:
        ha_comp = types.ModuleType("homeassistant.components")
        ha_comp.__path__ = []
        sys.modules["homeassistant.components"] = ha_comp

    if "homeassistant.components.repairs" not in sys.modules:
        ha_repairs = types.ModuleType("homeassistant.components.repairs")
        ha_repairs.RepairsFlow = MagicMock
        sys.modules["homeassistant.components.repairs"] = ha_repairs

    if "homeassistant.components.sensor" not in sys.modules:
        ha_sensor = types.ModuleType("homeassistant.components.sensor")
        ha_sensor.SensorEntity = MagicMock
        sys.modules["homeassistant.components.sensor"] = ha_sensor

    if "homeassistant.components.binary_sensor" not in sys.modules:
        ha_bsensor = types.ModuleType("homeassistant.components.binary_sensor")
        ha_bsensor.BinarySensorEntity = MagicMock
        ha_bsensor.BinarySensorDeviceClass = MagicMock
        sys.modules["homeassistant.components.binary_sensor"] = ha_bsensor

    if "homeassistant.components.calendar" not in sys.modules:
        ha_calendar = types.ModuleType("homeassistant.components.calendar")
        ha_calendar.CalendarEntity = MagicMock
        ha_calendar.CalendarEvent = MagicMock
        sys.modules["homeassistant.components.calendar"] = ha_calendar

    # Mock config_entries
    if "homeassistant.config_entries" not in sys.modules:
        ha_ce = types.ModuleType("homeassistant.config_entries")
        sys.modules["homeassistant.config_entries"] = ha_ce
        ha_ce.SOURCE_USER = "user"
        ha_ce.CONN_CLASS_CLOUD_POLL = "cloud_poll"

        class MockBase:
            def __init_subclass__(cls, **kwargs):
                pass

        ha_ce.ConfigFlow = MockBase
        ha_ce.OptionsFlow = MockBase

        class ConfigEntry:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
                self.options = kwargs.get("options", {})
                self.data = kwargs.get("data", {})
                self.entry_id = kwargs.get("entry_id", "mock_entry_id")

        ha_ce.ConfigEntry = ConfigEntry

    # Mock helpers
    if "homeassistant.helpers" not in sys.modules:
        ha_helpers = types.ModuleType("homeassistant.helpers")
        ha_helpers.__path__ = []
        sys.modules["homeassistant.helpers"] = ha_helpers

    if "homeassistant.helpers.config_validation" not in sys.modules:
        sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
    if "homeassistant.helpers.update_coordinator" not in sys.modules:
        ha_uc = types.ModuleType("homeassistant.helpers.update_coordinator")

        class DataUpdateCoordinator:
            def __init__(
                self,
                hass,
                logger,
                *,
                name,
                update_interval=None,
                update_method=None,
                request_refresh_debouncer=None
            ):
                self.hass = hass
                self.logger = logger
                self.name = name
                self.update_interval = update_interval
                self.update_method = update_method
                self.data = None

            async def _async_update_data(self):
                return None

            async def async_config_entry_first_refresh(self):
                pass

            async def async_refresh(self):
                pass

        ha_uc.DataUpdateCoordinator = DataUpdateCoordinator

        class StubCoordinatorEntity:
            """Stub for CoordinatorEntity."""

            last_update_success = True

            def __init__(self, coordinator, config_entry=None):
                self.__dict__["coordinator"] = coordinator
                self.__dict__["hass"] = getattr(coordinator, "hass", None)

            def __setattr__(self, name, value):
                self.__dict__[name] = value

            def __getattr__(self, name):
                if name in {
                    "_mock_methods",
                    "_mock_unsafe",
                    "_spec_set",
                    "_spec_class",
                }:
                    raise AttributeError(name)
                return self.__dict__.get(name, None)

            def _handle_coordinator_update(self):
                pass

            async def async_added_to_hass(self):
                pass

            async def async_will_remove_from_hass(self):
                pass

            @property
            def extra_state_attributes(self):
                return {}

        ha_uc.CoordinatorEntity = StubCoordinatorEntity
        sys.modules["homeassistant.helpers.update_coordinator"] = ha_uc
    if "homeassistant.helpers.aiohttp_client" not in sys.modules:
        sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
    if "homeassistant.helpers.frame" not in sys.modules:
        # Create a proper frame helper mock
        frame_helper = types.ModuleType("homeassistant.helpers.frame")

        # Mock the frame helper functions
        frame_helper.MissingIntegrationFrame = Exception
        frame_helper.get_integration_frame = MagicMock(return_value=None)
        frame_helper.report = MagicMock()

        sys.modules["homeassistant.helpers.frame"] = frame_helper

    if "homeassistant.helpers.issue_registry" not in sys.modules:
        ha_ir = types.ModuleType("homeassistant.helpers.issue_registry")
        ha_ir.IssueSeverity = MagicMock
        ha_ir.async_delete_issue = MagicMock()
        ha_ir.async_create_issue = MagicMock()
        sys.modules["homeassistant.helpers.issue_registry"] = ha_ir

    if "homeassistant.helpers.entity" not in sys.modules:
        ha_entity = types.ModuleType("homeassistant.helpers.entity")
        ha_entity.EntityCategory = MagicMock
        sys.modules["homeassistant.helpers.entity"] = ha_entity

    if "homeassistant.helpers.entity_platform" not in sys.modules:
        sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()

    # Mock util
    if "homeassistant.util" not in sys.modules:
        ha_util = types.ModuleType("homeassistant.util")
        ha_util.__path__ = []
        sys.modules["homeassistant.util"] = ha_util

    # Create a real stub for homeassistant.util.dt with datetime functions
    if "homeassistant.util.dt" not in sys.modules:
        from datetime import datetime, timezone

        ha_util_dt = types.ModuleType("homeassistant.util.dt")

        def parse_datetime(dt_str):
            """Parse ISO datetime string to timezone-aware datetime."""
            if not dt_str:
                return None
            try:
                # Try parsing with timezone info
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                return datetime.fromisoformat(dt_str)
            except (ValueError, AttributeError):
                return None

        def now():
            """Return current timezone-aware datetime."""
            return datetime.now(timezone.utc)

        ha_util_dt.parse_datetime = parse_datetime
        ha_util_dt.now = now
        sys.modules["homeassistant.util.dt"] = ha_util_dt

    # Mock homeassistant.util.logging
    if "homeassistant.util.logging" not in sys.modules:
        sys.modules["homeassistant.util.logging"] = MagicMock()

    # Mock core
    if "homeassistant.core" not in sys.modules:
        sys.modules["homeassistant.core"] = MagicMock()

    # Mock data_entry_flow
    if "homeassistant.data_entry_flow" not in sys.modules:
        ha_def = types.ModuleType("homeassistant.data_entry_flow")
        sys.modules["homeassistant.data_entry_flow"] = ha_def
        ha_def.FlowResultType = MagicMock()
        ha_def.FlowResultType.FORM = "form"
        ha_def.FlowResultType.CREATE_ENTRY = "create_entry"
        ha_def.FlowResultType.MENU = "menu"
        ha_def.FlowResultType.ABORT = "abort"

    # 2. Mock async_timeout
    if "async_timeout" not in sys.modules:
        async_timeout_mod = types.ModuleType("async_timeout")

        async def async_enter(*args, **kwargs):
            return None

        async def async_exit(*args, **kwargs):
            return None

        timeout_ctx = MagicMock()
        timeout_ctx.__aenter__ = async_enter
        timeout_ctx.__aexit__ = async_exit
        async_timeout_mod.timeout = MagicMock(return_value=timeout_ctx)
        sys.modules["async_timeout"] = async_timeout_mod

    # 3. Mock pytest_homeassistant_custom_component if missing
    if "pytest_homeassistant_custom_component" not in sys.modules:
        phcc = types.ModuleType("pytest_homeassistant_custom_component")
        phcc.__path__ = []
        sys.modules["pytest_homeassistant_custom_component"] = phcc

        phcc_common = types.ModuleType("pytest_homeassistant_custom_component.common")
        phcc_common.MockConfigEntry = MagicMock
        sys.modules["pytest_homeassistant_custom_component.common"] = phcc_common

# 3. Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def setup_frame_helper():
    """Set up frame helper for the test session."""
    try:
        from homeassistant.helpers import frame

        # Initialize the frame helper's internal state
        if not hasattr(frame, "_REPORTED_INTEGRATIONS"):
            frame._REPORTED_INTEGRATIONS = set()
        if not hasattr(frame, "_INTEGRATION_FRAME"):
            frame._INTEGRATION_FRAME = {}
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture(autouse=True)
def enable_custom_integrations(monkeypatch):
    """Enable custom integrations and prevent frame helper errors."""
    try:
        from homeassistant.helpers import frame

        # Monkeypatch to prevent RuntimeError: Frame helper not set up
        def mock_get_integration_frame(*args, **kwargs):
            return None

        monkeypatch.setattr(
            frame, "get_integration_frame", mock_get_integration_frame, raising=False
        )
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture
def hass():
    """Mock Hass fixture."""
    mock_hass = MagicMock()

    # Properly mock Config Entries
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.flow = MagicMock()
    mock_hass.config_entries.flow.async_init = AsyncMock(
        return_value={"type": "form", "step_id": "user"}
    )
    mock_hass.config_entries.flow.async_configure = AsyncMock(
        return_value={"type": "form", "step_id": "station"}
    )

    # Properly mock Options
    mock_hass.config_entries.options = MagicMock()
    mock_hass.config_entries.options.async_init = AsyncMock(
        return_value={"type": "menu", "flow_id": "mock_flow_id"}
    )
    mock_hass.config_entries.options.async_configure = AsyncMock(
        return_value={
            "type": "form",
            "flow_id": "mock_flow_id",
            "step_id": "general_options",
        }
    )

    mock_hass.config_entries.async_entries.return_value = []
    mock_hass.data = {}
    return mock_hass


@pytest.fixture
def mock_setup_entry():
    """Mock async_setup_entry fixture."""
    from unittest.mock import patch

    with patch(
        "custom_components.db_infoscreen.async_setup_entry", return_value=True
    ) as mock:
        yield mock

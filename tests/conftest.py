"""Global fixtures and mocks for db_infoscreen integration tests."""

import sys
import os
import types
from unittest.mock import MagicMock, AsyncMock

# 1. Mock homeassistant before any component imports
if "homeassistant" not in sys.modules:
    ha = types.ModuleType("homeassistant")
    ha.__path__ = []
    sys.modules["homeassistant"] = ha

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
    ha_ce.ConfigEntry = MagicMock

# Mock helpers
if "homeassistant.helpers" not in sys.modules:
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = ha_helpers

if "homeassistant.helpers.config_validation" not in sys.modules:
    sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
if "homeassistant.helpers.update_coordinator" not in sys.modules:
    sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
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

# 3. Add project root to path
sys.path.append(os.getcwd())

import pytest


@pytest.fixture
def hass():
    """Mock Hass fixture."""
    mock_hass = MagicMock()
    mock_hass.config_entries.flow = AsyncMock()
    mock_hass.config_entries.options = AsyncMock()
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


@pytest.fixture(autouse=True)
def fail_on_log_exception(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fixture to make tests fail on logged exceptions."""
    # This fixture is used by pytest-homeassistant-custom-component
    # We provide a no-op version for local testing
    pass

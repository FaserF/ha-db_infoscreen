"""Home Assistant Repairs for DB Infoscreen integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, CONF_DATA_SOURCE, DATA_SOURCE_OPTIONS

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_STALE_DATA = "stale_data"
ISSUE_API_ERROR = "api_error"
ISSUE_STATION_UNSUPPORTED = "station_unsupported"
ISSUE_CONNECTION_ERROR = "connection_error"

# GitHub issue URL for reporting
GITHUB_ISSUES_URL = "https://faserf.github.io/ha-db_infoscreen/"


def create_stale_data_issue(
    hass: HomeAssistant,
    entry_id: str,
    station: str,
    hours_stale: int,
) -> None:
    """Create a repair issue for stale data (not updated for 24+ hours)."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_STALE_DATA}_{entry_id}",
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_STALE_DATA,
        translation_placeholders={
            "station": station,
            "hours": str(hours_stale),
        },
        learn_more_url=GITHUB_ISSUES_URL,
    )


def create_api_error_issue(
    hass: HomeAssistant,
    entry_id: str,
    station: str,
    error_message: str,
) -> None:
    """Create a repair issue for persistent API errors."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_API_ERROR}_{entry_id}",
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_API_ERROR,
        translation_placeholders={
            "station": station,
            "error": error_message,
        },
        learn_more_url=GITHUB_ISSUES_URL,
    )


def create_station_unsupported_issue(
    hass: HomeAssistant,
    entry_id: str,
    station: str,
    data_source: str,
) -> None:
    """Create a repair issue when station may no longer be supported by the backend."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_STATION_UNSUPPORTED}_{entry_id}",
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_STATION_UNSUPPORTED,
        translation_placeholders={
            "station": station,
            "data_source": data_source,
        },
        learn_more_url=GITHUB_ISSUES_URL,
    )


def create_connection_error_issue(
    hass: HomeAssistant,
    entry_id: str,
    station: str,
) -> None:
    """Create a repair issue for connection errors (self-healing)."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CONNECTION_ERROR}_{entry_id}",
        is_fixable=False,  # Self-heals when connection is restored
        is_persistent=False,  # Will be cleared on restart/recovery
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_CONNECTION_ERROR,
        translation_placeholders={
            "station": station,
        },
    )


def delete_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Delete a repair issue when the problem is resolved."""
    ir.async_delete_issue(hass, DOMAIN, issue_id)


def clear_all_issues_for_entry(hass: HomeAssistant, entry_id: str) -> None:
    """Clear all repair issues related to a specific config entry."""
    for issue_type in [
        ISSUE_STALE_DATA,
        ISSUE_API_ERROR,
        ISSUE_STATION_UNSUPPORTED,
        ISSUE_CONNECTION_ERROR,
    ]:
        ir.async_delete_issue(hass, DOMAIN, f"{issue_type}_{entry_id}")


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create flow to fix a repairs issue."""
    if issue_id.startswith(ISSUE_STALE_DATA):
        return StaleDataRepairFlow(issue_id)
    if issue_id.startswith(ISSUE_API_ERROR):
        return APIErrorRepairFlow(issue_id)
    if issue_id.startswith(ISSUE_STATION_UNSUPPORTED):
        return StationUnsupportedRepairFlow(issue_id)
    # Default flow for unknown issues
    return ConfirmRepairFlow(issue_id)


class ConfirmRepairFlow(RepairsFlow):
    """Handler for simple confirmation repair flows."""

    def __init__(self, issue_id: str) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="init")


class StaleDataRepairFlow(RepairsFlow):
    """Repair flow for stale data issues - attempts to refresh data."""

    def __init__(self, issue_id: str) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        # Extract entry_id from issue_id (format: stale_data_<entry_id>)
        self._entry_id = issue_id.replace(f"{ISSUE_STALE_DATA}_", "")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step - offer to retry or change settings."""
        if user_input is not None:
            if user_input.get("action") == "retry":
                # Attempt to refresh the coordinator
                if self._entry_id in self.hass.data.get(DOMAIN, {}):
                    coordinator = self.hass.data[DOMAIN][self._entry_id]
                    await coordinator.async_request_refresh()
                    # Delete the issue
                    ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
                return self.async_create_entry(data={})
            elif user_input.get("action") == "report":
                # Redirect to GitHub issues (handled by frontend via learn_more_url)
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="retry"): vol.In(
                        {
                            "retry": "Retry fetching data now",
                            "report": "Report issue on GitHub",
                        }
                    )
                }
            ),
        )


class APIErrorRepairFlow(RepairsFlow):
    """Repair flow for API errors - allows changing data source."""

    def __init__(self, issue_id: str) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        self._entry_id = issue_id.replace(f"{ISSUE_API_ERROR}_", "")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            if user_input.get("action") == "retry":
                if self._entry_id in self.hass.data.get(DOMAIN, {}):
                    coordinator = self.hass.data[DOMAIN][self._entry_id]
                    await coordinator.async_request_refresh()
                    ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
                return self.async_create_entry(data={})
            elif user_input.get("action") == "change_source":
                return await self.async_step_change_source()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="retry"): vol.In(
                        {
                            "retry": "Retry fetching data",
                            "change_source": "Change data source",
                        }
                    )
                }
            ),
        )

    async def async_step_change_source(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Allow user to change the data source."""
        if user_input is not None:
            # Update the config entry with new data source
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry:
                new_data = {
                    **entry.data,
                    CONF_DATA_SOURCE: user_input[CONF_DATA_SOURCE],
                }
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="change_source",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(
                        DATA_SOURCE_OPTIONS
                    ),
                }
            ),
        )


class StationUnsupportedRepairFlow(RepairsFlow):
    """Repair flow when station may no longer be supported."""

    def __init__(self, issue_id: str) -> None:
        """Initialize the repair flow."""
        self._issue_id = issue_id
        self._entry_id = issue_id.replace(f"{ISSUE_STATION_UNSUPPORTED}_", "")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "retry":
                if self._entry_id in self.hass.data.get(DOMAIN, {}):
                    coordinator = self.hass.data[DOMAIN][self._entry_id]
                    await coordinator.async_request_refresh()
                    ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
                return self.async_create_entry(data={})
            elif action == "change_source":
                return await self.async_step_change_source()
            elif action == "remove":
                # Remove the associated repair issue first
                ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
                # Remove the config entry
                entry = self.hass.config_entries.async_get_entry(self._entry_id)
                if entry:
                    await self.hass.config_entries.async_remove(self._entry_id)
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="retry"): vol.In(
                        {
                            "retry": "Try again",
                            "change_source": "Change data source",
                            "remove": "Remove this station",
                        }
                    )
                }
            ),
            description_placeholders={
                "station": self.hass.config_entries.async_get_entry(
                    self._entry_id
                ).data.get("station", "Unknown"),
                "data_source": self.hass.config_entries.async_get_entry(
                    self._entry_id
                ).data.get("data_source", "Unknown"),
                "docs_url": GITHUB_ISSUES_URL,
            },
        )

    async def async_step_change_source(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Allow user to change the data source."""
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry:
                new_data = {
                    **entry.data,
                    CONF_DATA_SOURCE: user_input[CONF_DATA_SOURCE],
                }
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="change_source",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DATA_SOURCE, default="IRIS-TTS"): vol.In(
                        DATA_SOURCE_OPTIONS
                    ),
                }
            ),
        )

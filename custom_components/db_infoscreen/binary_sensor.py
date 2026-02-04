"""Binary sensor platform for DB Infoscreen integration."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DBInfoScreenBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DB Infoscreen binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            DBInfoScreenDelayBinarySensor(coordinator, config_entry),
            DBInfoScreenCancellationBinarySensor(coordinator, config_entry),
            DBInfoScreenConnectionBinarySensor(coordinator, config_entry),
        ]
    )

    # Add Elevator Sensors
    # If platforms are filtered, create sensors for those platforms.
    # Otherwise, we could create a general one or try to infer from typical usage.
    # For now, if 'platforms' config exists, we create one for each.
    # If not, we create a general "Station Accessibility" sensor.
    platforms_str = config_entry.data.get("platforms", "")
    if platforms_str:
        platforms = [p.strip() for p in platforms_str.split(",")]
        for platform in platforms:
            async_add_entities(
                [DBInfoScreenElevatorBinarySensor(coordinator, config_entry, platform)]
            )
    else:
        async_add_entities(
            [DBInfoScreenElevatorBinarySensor(coordinator, config_entry, None)]
        )


class DBInfoScreenBaseBinarySensor(DBInfoScreenBaseEntity, BinarySensorEntity):
    """Base class for DB Infoscreen binary sensors."""

    def __init__(self, coordinator, config_entry: ConfigEntry, station: str = None) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry)
        self.station_name = station  # Store station or platform context if needed


class DBInfoScreenDelayBinarySensor(DBInfoScreenBaseBinarySensor):
    """Binary sensor that indicates if any train is delayed."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the delay sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"db_infoscreen_delay_{config_entry.entry_id}"
        self._attr_name = "Delay"
        self._attr_icon = "mdi:clock-alert"

    @property
    def is_on(self) -> bool:
        """Return True if any train is delayed."""
        departures = self.coordinator.data or []
        for departure in departures:
            delay = departure.get("delay", departure.get("delayDeparture", 0))
            try:
                if delay and int(delay) > 0:
                    return True
            except (ValueError, TypeError):
                pass
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes about delays."""
        departures = self.coordinator.data or []
        delayed_trains = []
        max_delay = 0

        for departure in departures:
            delay = departure.get("delay", departure.get("delayDeparture", 0))
            try:
                delay_int = int(delay) if delay else 0
                if delay_int > 0:
                    line = departure.get("line", departure.get("train", "Unknown"))
                    destination = departure.get("destination", "Unknown")
                    delayed_trains.append(
                        {
                            "line": line,
                            "destination": destination,
                            "delay_minutes": delay_int,
                        }
                    )
                    max_delay = max(max_delay, delay_int)
            except (ValueError, TypeError):
                pass

        return {
            "delayed_trains": delayed_trains,
            "delayed_count": len(delayed_trains),
            "max_delay_minutes": max_delay,
        }


class DBInfoScreenCancellationBinarySensor(DBInfoScreenBaseBinarySensor):
    """Binary sensor that indicates if any train is cancelled."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the cancellation sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"db_infoscreen_cancelled_{config_entry.entry_id}"
        self._attr_name = "Cancellation"
        self._attr_icon = "mdi:train-car-passenger-door"

    @property
    def is_on(self) -> bool:
        """Return True if any train is cancelled."""
        departures = self.coordinator.data or []
        for departure in departures:
            if (
                departure.get("isCancelled", False)
                or departure.get("is_cancelled", False)
                or departure.get("cancelled", False)
            ):
                return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes about cancellations."""
        departures = self.coordinator.data or []
        cancelled_trains = []

        for departure in departures:
            if (
                departure.get("isCancelled", False)
                or departure.get("is_cancelled", False)
                or departure.get("cancelled", False)
            ):
                line = departure.get("line", departure.get("train", "Unknown"))
                destination = departure.get("destination", "Unknown")
                cancelled_trains.append(
                    {
                        "line": line,
                        "destination": destination,
                    }
                )

        return {
            "cancelled_trains": cancelled_trains,
            "cancelled_count": len(cancelled_trains),
        }


class DBInfoScreenConnectionBinarySensor(DBInfoScreenBaseBinarySensor):
    """Binary sensor that indicates if the API connection is healthy."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False  # Disabled by default

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the connection sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"db_infoscreen_connection_{config_entry.entry_id}"
        self._attr_name = "API Connection"
        self._attr_icon = "mdi:api"

    @property
    def is_on(self) -> bool:
        """Return True if connection is healthy."""
        return (
            self.coordinator.last_update_success
            if hasattr(self.coordinator, "last_update_success")
            else False
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return connection details."""
        last_update = getattr(self.coordinator, "last_update", None)
        consecutive_errors = getattr(self.coordinator, "_consecutive_errors", 0)

        return {
            "api_url": getattr(self.coordinator, "api_url", "Unknown"),
            "last_successful_update": (
                last_update.isoformat() if last_update else "Never"
            ),
            "consecutive_errors": consecutive_errors,
        }


class DBInfoScreenElevatorBinarySensor(DBInfoScreenBaseBinarySensor):
    """Binary sensor that indicates if an elevator/escalator is broken."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False  # Disabled by default as requested

    def __init__(self, coordinator, config_entry: ConfigEntry, platform: str | None) -> None:
        """Initialize the elevator sensor."""
        super().__init__(coordinator, config_entry)
        self.platform_filter = platform

        if platform:
            self._attr_unique_id = f"db_infoscreen_elevator_{platform}_{config_entry.entry_id}"
            self._attr_name = f"Elevator Platform {platform}"
        else:
            self._attr_unique_id = f"db_infoscreen_elevator_general_{config_entry.entry_id}"
            self._attr_name = "Station Accessibility"

        self._attr_icon = "mdi:elevator-passenger-off-outline"

    @property
    def is_on(self) -> bool:
        """Return True if a relevant issue is found."""
        return len(self.get_issues()) > 0

    def get_issues(self) -> list[str]:
        """Parse departures for relevant elevator issues."""
        departures = self.coordinator.data or []
        issues = set()

        # Keywords to look for
        keywords = ["aufzug", "aufzüge", "fahrstuhl", "lift", "rolltreppe"]

        for departure in departures:
            messages = departure.get("messages", {})
            # Collect all message texts
            texts = []
            if isinstance(messages, dict):
                for msg_type in messages:
                    msg_list = messages[msg_type]
                    if isinstance(msg_list, list):
                        for m in msg_list:
                            if isinstance(m, dict):
                                texts.append(m.get("text", ""))
                            elif isinstance(m, str):
                                texts.append(m)

            for text in texts:
                lower_text = text.lower()
                # Check for elevator keywords
                if any(k in lower_text for k in keywords):
                    # Check for platform relevance
                    # If we filter by platform, only include if matches platform OR is global?
                    # "Aufzug Gleis 1 defekt" -> Match "1"

                    is_relevant = False
                    if self.platform_filter:
                        # Check strictly for this platform
                        # Regex to find platform number in text
                        match = re.search(r"(?:gleis|bahnsteig)\s*(\d+)", lower_text)
                        if match:
                            if match.group(1) == self.platform_filter:
                                is_relevant = True
                        else:
                            # No platform mentioned?
                            # If we are filtering for a specific platform, assume specific messages only
                            # unless we explicitly decide otherwise.
                            # Changing default behavior as requested:
                            is_relevant = False
                    else:
                        # No filter -> All matches are relevant
                        is_relevant = True

                    if is_relevant:
                        issues.add(text)

        return list(issues)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about elevator issues."""
        issues = self.get_issues()
        return {
            "issues": issues,
            "issue_count": len(issues),
        }

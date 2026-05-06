"""Lovelace dashboard and view strategies for DB Infoscreen."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


class DBInfoscreenDashboardStrategy:
    """Strategy to generate a complete DB Infoscreen dashboard."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the strategy."""
        self.hass = hass

    async def async_generate(self, info: dict[str, Any]) -> dict[str, Any]:
        """Generate a dashboard configuration."""

        view_strategy = DBInfoscreenViewStrategy(self.hass)
        main_view = await view_strategy.async_generate(info)

        return {"views": [main_view]}


class DBInfoscreenViewStrategy:
    """Strategy to generate a single DB Infoscreen view."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the strategy."""
        self.hass = hass

    async def async_generate(self, info: dict[str, Any]) -> dict[str, Any]:
        """Generate a view configuration."""
        hass = self.hass

        # 1. Find all db_infoscreen sensors
        entities = [
            state.entity_id
            for state in hass.states.async_all()
            if state.entity_id.startswith("sensor.")
            and "departures" in state.entity_id
            and state.attributes.get("attribution", "").lower().find("dbf") != -1
        ]

        # 2. Find weather (optional)
        weather_entity = next(
            (e for e in hass.states.async_entity_ids("weather")), None
        )

        # 3. Build the Sections View
        view_config: dict[str, Any] = {
            "title": "Departure Board",
            "path": "departures",
            "type": "sections",
            "max_columns": 3,
            "sections": [],
        }

        # Header Section (Weather + Announcements)
        header_cards = []
        if weather_entity:
            header_cards.append(
                {
                    "type": "weather-forecast",
                    "entity": weather_entity,
                    "show_forecast": False,
                }
            )

        if header_cards:
            view_config["sections"].append({"title": "Overview", "cards": header_cards})

        if not entities:
            view_config["sections"].append(
                {
                    "title": "Setup Required",
                    "cards": [
                        {
                            "type": "button",
                            "name": "Add Station",
                            "icon": "mdi:plus",
                            "action_name": "Configure",
                            "tap_action": {
                                "action": "navigate",
                                "navigation_path": "/config/integrations",
                            },
                        }
                    ],
                }
            )
            return view_config

        # 4. Main Departure Sections
        for entity_id in entities:
            state = hass.states.get(entity_id)
            station_name = (
                state.attributes.get("station", "Station") if state else "Station"
            )

            # Create a section for each station
            station_section: dict[str, Any] = {
                "title": station_name,
                "cards": [
                    {
                        "type": "custom:db-infoscreen-card",
                        "entity": entity_id,
                        "count": 6,
                    }
                ],
            }

            # Optional: Add a watchdog sensor card if it exists for this entry
            watchdog_id = entity_id.replace("departures", "trip_watchdog")
            if hass.states.get(watchdog_id):
                station_section["cards"].append(
                    {
                        "type": "entity",
                        "entity": watchdog_id,
                        "name": "Live Trip Watchdog",
                    }
                )

            view_config["sections"].append(station_section)

        return view_config

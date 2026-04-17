
"""Lovelace dashboard and view strategies for DB Infoscreen."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lovelace.strategies import LovelaceStrategy
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

class DBInfoscreenDashboardStrategy(LovelaceStrategy):
    """Strategy to generate a complete DB Infoscreen dashboard."""

    async def async_generate(self, info: dict[str, Any]) -> dict[str, Any]:
        """Generate a dashboard configuration."""
        
        # Build views using the view strategy logic
        view_strategy = DBInfoscreenViewStrategy(self.hass)
        main_view = await view_strategy.async_generate(info)

        return {
            "views": [main_view]
        }

class DBInfoscreenViewStrategy(LovelaceStrategy):
    """Strategy to generate a single DB Infoscreen view."""

    async def async_generate(self, info: dict[str, Any]) -> dict[str, Any]:
        """Generate a view configuration."""
        hass = self.hass
        
        # 1. Find all db_infoscreen sensors
        entities = [
            entity_id
            for entity_id, state in hass.states.async_all()
            if entity_id.startswith("sensor.") and "departures" in entity_id
            and state.attributes.get("attribution", "").lower().find("dbf") != -1
        ]

        # 2. Build the Sections View
        view_config = {
            "title": "Departure Board",
            "path": "departures",
            "type": "sections", # HA 2026 Standard for modern dashboards
            "max_columns": 3,
            "sections": []
        }

        # Group entities if there are many, otherwise put in one section
        if not entities:
            view_config["sections"].append({
                "title": "Setup Required",
                "cards": [
                    {
                        "type": "button",
                        "name": "Add Station",
                        "icon": "mdi:plus",
                        "action_name": "Configure",
                        "tap_action": {
                            "action": "navigate",
                            "navigation_path": "/config/integrations"
                        }
                    }
                ]
            })
            return view_config

        # Create sections for stations
        for entity_id in entities:
            state = hass.states.get(entity_id)
            station_name = state.attributes.get("station", "Station") if state else "Station"
            
            view_config["sections"].append({
                "title": station_name,
                "cards": [
                    {
                        "type": "custom:db-infoscreen-card",
                        "entity": entity_id,
                        "count": 6
                    }
                ]
            })

        return view_config

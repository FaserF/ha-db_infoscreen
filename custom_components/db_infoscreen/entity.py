"""Base entity for DB Infoscreen."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


class DBInfoScreenBaseEntity(CoordinatorEntity):
    """Base entity class for DB Infoscreen."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry):
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        # Some entities use 'station' directly from data, others might need it from local attr
        self.station = config_entry.data.get("station", "Unknown")

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": f"DB Infoscreen {self.config_entry.title}",
            "manufacturer": "DBF (derf)",
            "model": "Departure Board",
            "configuration_url": getattr(self.coordinator, "web_url", None),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            if hasattr(self.coordinator, "last_update_success")
            else False
        )

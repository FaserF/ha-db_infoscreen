# Entities Reference 📊

The DB Infoscreen integration creates multiple entities for each configured station to provide comprehensive departure information.

---

## 🚦 Sensor Entities

### Main Departure Sensor
The primary sensor that displays the next departure time.

| Attribute | Description |
| :--- | :--- |
| `state` | Scheduled departure time of the next train |
| `next_departures` | List of all upcoming departures with full details |
| `station` | Configured station name |
| `last_updated` | Last successful data refresh |
| `attribution` | Data source URL |

**Attributes per Departure:**
- `line` - Train line/number (e.g., "ICE 578", "S3")
- `destination` - Final destination
- `platform` / `scheduledPlatform` - Current and planned platform
- `delay` / `delayDeparture` - Delay in minutes
- `isCancelled` - Whether the train is cancelled
- `route` - Intermediate stops (if enabled)
- `messages` - Quality notes and warnings
- `wagon_order` - Raw wagon order data (if available and detailed)
- `wagon_order_html` - HTML summary of wagon order (e.g. "1. Class in A")

---

### Trip Watchdog Sensor
**Entity ID**: `sensor.db_infoscreen_{station}_trip_watchdog`

!!! note "Disabled by Default"
    This sensor is disabled by default. Enable it if you want to monitor the status of the next train at its previous stop.

| State | Meaning |
| :--- | :--- |
| **{Station}: +X min** | Train left previous station with X minute delay |
| **{Station}: On Time** | Train left previous station on time |
| **Unknown** | No route data available |

**Attributes:**
- `train` - Train identifier (e.g. "ICE 578")
- `previous_station_name` - Name of the previous station
- `previous_delay` - Delay in minutes at previous station

---

## 🔴 Binary Sensors

Three binary sensors are automatically created to provide quick status indicators.

### Delay Sensor
**Entity ID**: `binary_sensor.db_infoscreen_{station}_delay`

!!! note "Disabled by Default"
    This sensor is disabled by default. Enable it in the entity settings if you wish to track delays.

| State | Meaning |
| :--- | :--- |
| **ON** | At least one train is delayed (>0 minutes) |
| **OFF** | All trains are on time |

**Attributes:**
- `delayed_trains` - List of delayed train details
- `max_delay` - Highest delay in minutes
- `delayed_count` - Number of delayed trains

!!! example "Automation Example"
    ```yaml
    trigger:
      - platform: state
        entity_id: binary_sensor.db_infoscreen_muenchen_hbf_delay
        to: "on"
    action:
      - service: notify.mobile
        data:
          title: "🚆 Train Delay"
          message: "Trains at München Hbf are delayed!"
    ```

---

### Cancellation Sensor
**Entity ID**: `binary_sensor.db_infoscreen_{station}_cancellation`

!!! note "Disabled by Default"
    This sensor is disabled by default. Enable it in the entity settings if you wish to track cancellations.

| State | Meaning |
| :--- | :--- |
| **ON** | At least one train is cancelled |
| **OFF** | No cancellations |

**Attributes:**
- `cancelled_trains` - List of cancelled train details
- `cancelled_count` - Number of cancelled trains

---

### API Connection Sensor (Diagnostic)
**Entity ID**: `binary_sensor.db_infoscreen_{station}_api_connection`

!!! note "Disabled by Default"
    This sensor is disabled by default. Enable it in the entity settings if you need to monitor API health.

| State | Meaning |
| :--- | :--- |
| **ON** | API connection is healthy |
| **OFF** | Connection issues detected |

**Attributes:**
- `last_successful_update` - Timestamp of last successful data fetch
- `consecutive_errors` - Number of consecutive API failures

---

---

### Accessibility Sensor (Elevator)
**Entity ID**: `binary_sensor.db_infoscreen_{station}_elevator_{platform}` or `_general_`

!!! note "Disabled by Default"
    This sensor is disabled by default. Enable it in the entity settings if you require accessibility information.

| State | Meaning |
| :--- | :--- |
| **ON** | Elevator or escalator issue detected |
| **OFF** | No reported issues |

**Attributes:**
- `issues` - List of specific issue messages (e.g. "Aufzug zu Gleis 1 defekt")
- `issue_count` - Number of active issues

---

## 📅 Calendar Entity

**Entity ID**: `calendar.db_infoscreen_{station}_departures`

!!! note "Disabled by Default"
    The calendar entity is disabled by default. Enable it in the entity settings when you want to visualize departures on a calendar view.

The calendar entity converts each departure into a calendar event, perfect for:
- Visual dashboard calendars
- Lovelace calendar cards
- Integration with other calendar tools

### Event Format

| Property | Example |
| :--- | :--- |
| **Summary** | `ICE 578 → Berlin Hbf (+5min)` |
| **Start** | Scheduled departure time |
| **Duration** | 5 minutes (represents boarding window) |
| **Location** | `Platform 12, München Hbf` |
| **Description** | Line, destination, platform, delay, route details |

**Special Indicators in Summary:**
- `(+Xmin)` - Delay indicator
- `⚠️ CANCELLED` - Cancellation warning

!!! tip "Calendar Card"
    Add a calendar card to your dashboard:
    ```yaml
    type: calendar
    entities:
      - calendar.db_infoscreen_muenchen_hbf_departures
    ```

---

## 🔧 Repair Support

The integration automatically monitors for issues and creates repair entries in **Settings → System → Repairs**.

### Issue Types

| Issue | Description | Auto-Resolves? |
| :--- | :--- | :--- |
| **Stale Data** | No successful data update for 24+ hours | ✅ On next success |
| **API Error** | 3+ consecutive API failures | ✅ On next success |
| **Station Unsupported** | 10+ failures, station may be invalid | ❌ Manual action |
| **Connection Error** | Temporary network issue | ✅ On next success |

### Self-Healing Actions
When you view a repair issue, you can choose:
- **Retry** - Attempt to fetch data again
- **Change Data Source** - Switch to a different backend
- **Remove Station** - Delete the problematic configuration

---

## 🗂️ Device Grouping

All entities for a station are grouped under a single device:

| Property | Value |
| :--- | :--- |
| **Name** | DB Infoscreen {Station} |
| **Manufacturer** | Deutsche Bahn |
| **Model** | Departure Board |

This allows you to:
- View all entities in one place
- Add the device to areas
- Use device triggers in automations

---

## 🔗 Related Documentation
- [Configuration Reference](configuration.md)
- [Automation Cookbook](automations.md)
- [Troubleshooting](troubleshooting.md)

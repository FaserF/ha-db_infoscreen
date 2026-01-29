# Advanced Usage 🚀

For users who want to push the boundaries of their Home Assistant dashboard, `ha-db_infoscreen` provides several advanced features.

---

## 🛠️ Templating & Logic

The sensor stores its main payload in the `departures` attribute as a JSON list. This makes it incredibly easy to use Jinja2 templates for custom notifications or cards.

### Example: Delay Notification
Trigger an automation only if the next train toward "Mainz" is delayed by more than 10 minutes.

{% raw %}
```yaml
automation:
  - alias: "Commuter Delay Alert"
    trigger:
      - platform: template
        value_template: >
          {% set trains = state_attr('sensor.my_station', 'departures') %}
          {% if trains %}
            {{ (trains | selectattr('destination', 'search', 'Mainz') | first).delayDeparture | int > 10 }}
          {% else %}
            false
          {% endif %}
    action:
      - service: notify.mobile_app
        data:
          title: "🚆 Train Delay!"
          message: "The next train to Mainz is delayed by {{ (state_attr('sensor.my_station', 'departures') | selectattr('destination', 'search', 'Mainz') | first).delayDeparture }} minutes."
```
{% endraw %}

---

## 🔍 Attribute Reference

The `departures` list contains rich data objects. Here are the keys available for advanced templating:

| Key | Description | Example |
| :--- | :--- | :--- |
| `trip_id` | **Unique ID** for this specific train run. Constant even if times change. | `"123456789"` |
| `train` | Train type and number. | `"ICE 279"` |
| `destination` | Final destination. | `"Basel SBB"` |
| `platform` | Current platform. | `"6"` |
| `scheduledPlatform` | Original platform (check for changes!). | `"5"` |
| `changed_platform` | **Boolean**. True if `platform` != `scheduledPlatform`. | `true` |
| `wagon_order` | Link or basic info about wagon order. | `"https://..."` |
| `platform_sectors` | Extracted sector info for stopping position. | `"A-C"` |
| `facilities` | **QoS Data**. Dictionary of amenities. | `{"wifi": false, "bistro": true}` |
| `occupancy` | **Load Factor**. `1` (low) to `4` (full). | `2` |
| `route_details` | **Real-time Route**. List of stops with delays. | `[{"stop": "Hanau", "delay": 2}, ...]` |

### Example: Wagon Sector & Occupancy
```yaml
- type: markdown
  content: >
    {% set trains = state_attr('sensor.frankfurt_hbf', 'departures') %}
    {% if trains %}
      {% set t = trains[0] %}
      **Next Train**: {{ t.train }}
      **Platform**: {{ t.platform }} (Sectors: {{ t.platform_sectors }})
      **Occupancy**:
      {% if t.occupancy == 1 %} 🟢 (Low)
      {% elif t.occupancy == 2 %} 🟡 (Medium)
      {% elif t.occupancy == 3 %} 🟠 (High)
      {% elif t.occupancy == 4 %} 🔴 (Full)
      {% else %} ⚪ (Unknown)
      {% endif %}
    {% else %}
      No departures available.
    {% endif %}
```

---

## 📡 Self-Hosting the Backend

If you have a high number of sensors or want maximum privacy, you can host your own instance of the [db-fakedisplay](https://github.com/derf/db-fakedisplay) API.

### Docker Compose Example
```yaml
services:
  dbf:
    image: derf/db-fakedisplay:latest
    ports:
      - "8080:8080"
    restart: always
```

Once running, update the **Custom API URL** in the integration settings to:
`http://<your-ip>:8080`

---

## 🤖 Automated API Tracking

A unique feature of this project is its tight integration with the upstream backend.
-   **The Version File**: We maintain a `.backend_version` file in our repository.
-   **Renovate**: Our CI system (Renovate) monitors the `derf/db-fakedisplay` project for releases.
-   **Automatic Verification**: When a new version is released, Renovate creates a PR to update our tracked version. This triggers our GitHub Actions to run the full suite of stability tests against the new backend logic **before** you even receive an update.
-   **Reliability**: This ensures that `ha-db_infoscreen` remains compatible with backend changes without manual intervention.

!!! tip "Looking for Automations?"
    For practical examples of how to use these attributes in your automations, visit the [Automation Cookbook](automations.md).

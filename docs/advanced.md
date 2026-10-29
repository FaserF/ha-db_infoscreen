# Advanced Usage 🚀

For users who want to push the boundaries of their Home Assistant dashboard, `ha-db_infoscreen` provides several advanced features.

---

## 🛠️ Templating & Logic

The departures are provided as a list of dictionaries in the `departures` attribute. You can use standard Jinja2 filters:

-   `| first`: Get the very next train

-   `| selectattr('destination', 'search', 'Mainz')`: Filter for trains going to Mainz

-   `| map(attribute='delayDeparture')`: Extract a specific attribute from all items

The sensor stores its main payload in the `departures` attribute as a JSON list. This makes it incredibly easy to use Jinja2 templates for custom notifications or cards.

### Example: Delay Notification {: #example-delay-notification }

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
| `deduplication_key` | Internal key generated from the configured template used to identify unique journeys. | `"S2"` or `"12345"` |
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

### Example: Wagon Sector & Occupancy {: #example-wagon-sector-occupancy }

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

## 🧹 Deduplication Mastery {: #deduplication-mastery }
 
Deduplication is one of the most powerful and misunderstood features of `ha-db_infoscreen`. It is designed to handle "messy" data from transit providers where the same physical train might be reported multiple times (e.g., once for Platform 1 and once for "Platform 1a").
 
### 🧠 How it works behind the scenes
 
The integration applies a **120-second (2 minute) sliding window** to all fetched departures:
 
1.  **Sorting**: All incoming departures are sorted strictly by their **scheduled** departure time.
2.  **Key Generation**: For every single departure, the integration takes the **Deduplication Key Template** (e.g., `{line}{destination}`) and replaces the placeholders with the actual data of that train.
3.  **Comparison**: The integration compares the current train's key against the **last kept** train's key.
4.  **The Decision**: 
    *   If the **keys are identical** AND the **time difference is ≤ 120 seconds** -> The new train is considered a **duplicate** and is discarded.
    *   Otherwise -> The train is kept, and its key becomes the new "last kept" key for future comparisons.
 
### 🛠️ Building the Perfect Key
 
The "Key" is your way of telling the integration what makes a train unique.
 
 | Scenario | Recommended Key | Why? |
 | :--- | :--- | :--- |
 | **Deutsche Bahn (IRIS)** | `{journeyID}{journeyId}{id}{key}{trainNumber}` | **(Default)** DB provides stable, unique trip IDs. This key is very precise and only merges if it's the exact same technical run. |
 | **KVV / Local Trams** | `{line}` | **Highly Recommended**. Regional APIs often change trip IDs for every platform variation. By using just `{line}`, you tell the system: "I only want to see the S2 once every 2 minutes." |
 | **Commuter (Target)** | `{line}{destination}` | Perfect if you have multiple lines (S1, S2) going to the same place. It differentiates the lines but merges duplicates of the same line going to the same target. |
 | **The "Simple" Board** | `{destination}` | Best if you don't care which train you take, as long as it goes to your city. Any trains arriving within 2 minutes of each other at the same destination are merged. |
 
### 🕵️ Troubleshooting: "I still see duplicates!"
 
If your dashboard shows the same train twice, follow these exact steps to find the "Idiot-proof" fix:
 
1.  **Enable Details**: Go to **Configure -> Display Settings** and check **Detailed Information**.
2.  **Inspect Attributes**: Open the sensor's state in Home Assistant (Developer Tools -> States). Look for the `next_departures` attribute.
3.  **Find the Difference**: Compare the two duplicate entries. 
    *   *Example*: One train has `id: "123"` and the other has `id: "456"`.
    *   *Observation*: Because their IDs are different, the **Default Key** makes them "unique" in the eyes of the integration.
4.  **Simplify**: Identify a field that is **identical** for both duplicates (usually `line` or `destination`).
5.  **Apply**: Go to **Configure -> Advanced Options** and set the **Deduplication Key** to only that identical field (e.g., `{line}`).
6.  **Verify**: The duplicates should disappear on the next update.
 
!!! warning "Key Sensitivity"
    The Deduplication Key is **case-insensitive** and ignores all whitespace. `{LINE}` is the same as `{line}`.
 
---
 
## 📡 Self-Hosting the Backend {: #self-hosting }

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

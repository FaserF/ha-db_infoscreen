# Configuration Reference ⚙️

`ha-db_infoscreen` provides a multi-layered configuration system. You can set up basic sensors quickly or dive deep into filtering logic.

---

## 🏗️ Initial Configuration (The Wizard)

When you first add a "DB Infoscreen" integration, you meet the setup wizard. This creates the "Base Sensor".

| Option | Description | Required | Example |
| :--- | :--- | :--- | :--- |
| **Station** | Name, DS100 code, or EVA ID of the station. | **Yes** | `Berlin Hbf` or `8000105` |
| **Data Source** | Backend used to fetch data. `IRIS-TTS` is official DB data. | No | `IRIS-TTS` |
| **Departures** | How many upcoming trains should be tracked (Default: 4). | No | `5` |
| **Travel Time** | Minutes it takes you to walk to the station. | No | `5` |

!!! info "Station Search"
    The setup flow includes an **autocomplete search** to help find the correct official name. For more details, see the [Station Search Guide](station-search.md).

---

## 🛠️ Options Flow (Fine Tuning)

Once a sensor is created, click **Configure** on the integration card to access granular settings. These are categorized into meaningful groups. Use the "Finish and Save" button in the main menu to apply all changes at once.

### :material-clock-outline: General Options {: #general-options }
Basic update behavior and timing.

-   **Number of Upcoming Departures**: Updates the amount of tracked trains.
-   **Update Interval (minutes)**: How often the sensor polls the API. Default is 3 minutes.
-   **Offset (HH:MM)**: Shift the search window into the future. 
    -   *Example*: Use `00:15` if you want to skip all trains leaving in the next 15 minutes because you haven't left the house yet.
-   **Travel Time (minutes)**: Used for the "Leave Now" alarm logic.
-   **Pause periodic updates**: A master switch to stop all API requests for this station.
    -   *Why use this?*: To save server resources and prevent rate-limiting when you don't need the data (e.g., at night or when you are on vacation).
    -   *Monitoring*: You can monitor the pause state via the `is_paused` attribute on the main departures sensor or the (disabled by default) `Update Status` binary sensor.
    -   *How to automate?*: This is a simple `True/False` toggle. To create "schedules" or "location-based pausing", use Home Assistant automations. See the [Automation Cookbook](automations.md#smart-pausing) for "idiot-proof" examples.

### :material-filter-variant: Filter Options {: #filter-options }
Refine which trains are shown on your dashboard.

!!! important "Delimiter Rule"
    **Always use a comma `,`** to separate multiple values in text fields.

-   **Platforms**: Filter by platform names (e.g. `1, 4a, 5`).
-   **Via Stations**: Comma-separated list of stations the train must pass through.
-   **Via Station Logic**: 
    -   **OR** (Default): Shows trains stopping at *any* of the listed stations.
    -   **AND**: Shows only trains stopping at *all* listed stations.
-   **Direction**: A substring search for the destination (e.g. `München`).
-   **Excluded Directions**: Hide trains heading toward specific destinations.
-   **Ignored Train Types**: Multi-select list to hide `S-Bahn`, `Bus`, `ICE`, etc.
-   **Exclude Cancelled Trains**: 
    -   `True`: Cancelled trains vanish from your dashboard entirely.
    -   `False` (Default): Cancelled trains stay in the list (marked as `isCancelled: true`).
-   **Favorite Trains**: A comma-separated list of specific train names (e.g., `ICE 123, RE 5`) to filter the board for commuters.

### :material-monitor-dashboard: Display Options {: #display-options }
Control how data is presented in Home Assistant entities.

-   **Detailed Information**: Enables extra JSON metadata in attributes (e.g. full route details, trip IDs).
-   **Display Mode (admode)**:
    -   `preferred departure`: Planned time, switches to actual time if delayed.
    -   `departure`: Always shows planned/actual departure time.
    -   `arrival`: Shows arrival time (useful for tracking incoming trains).
-   **Enable Text View**: Compiles important info into a single formatted string, ideal for ESPHome/ePaper displays.
    -   **Text View Template**: Default is `{line} -> {destination} (Pl {platform}): {time}{delay_str}`.
-   **Hide Low Delay**: Removes delay noise for delays less than 5 minutes.
-   **Show Occupancy**: Enables fetching of train occupancy data (load factor 1-4) if available.

### :material-flask: Advanced Options {: #advanced-options }
Technical settings and provider-specific fixes.

-   **Custom API URL**: Essential if self-hosting a [db-fakedisplay](https://github.com/derf/db-fakedisplay) instance.
-   **Deduplicate Departures**: Filters out redundant entries. This is essential for providers like KVV where the same train might be reported for multiple platform variants simultaneously.
    -   **How it works**: The integration compares departures within a **120-second (2 minute) window**. If two departures generate the same **Deduplication Key**, the second one is hidden.
-   **Deduplication Key**: A template to identify a "unique" trip.
    -   **When to change this?**: If you still see the same train twice on your dashboard despite deduplication being enabled, your key is "too unique" (values differ between the duplicates).
    -   **Common Placeholders**:
        -   `{line}`: The train name (e.g., `S 2`).
        -   `{destination}`: Where it's going.
        -   `{id}` / `{key}` / `{journeyID}`: Unique IDs from the provider (often contain timestamps).
    -   **KVV / Regional Transport Tip**: Set this simply to `{line}`. This tells the system: "Only one S2 can leave every 2 minutes."
    -   **Troubleshooting**: Enable **Detailed Information** (Display Options) and look at the `departures` attribute. Compare the two duplicates. If they have different IDs but the same line, use `{line}` as your key.
-   **Keep Route Details**: Persists the full station list even if the API update is partial.
-   **Keep if Endstation**: Prevents the sensor from clearing data when reaching the final stop.
-   **Drop Late Trains**: Hide trains that have logically "departed" but are still in the system due to delay.
-   **Past 60 Minutes**: Include trains that left in the last hour.
-   **Data Source**: Switch between IRIS (DB) and regional HAFAS/EFA providers. See the [Data Sources Reference](data-sources.md).

---

### 🚀 Next Steps

- [Entities Reference](entities.md){ .md-button }
- [Automation Cookbook](automations.md){ .md-button }
- [Troubleshooting](troubleshooting.md){ .md-button }

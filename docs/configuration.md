# Configuration Reference ⚙️

`ha-db_infoscreen` provides a multi-layered configuration system. You can set up basic sensors quickly or dive deep into filtering logic.

---

## 🏗️ Initial Configuration (The Wizard)

When you first add a "DB Infoscreen" integration, you meet the setup wizard. This creates the "Base Sensor".

### 1. Station Selection
-   **Search & Select**: Simply type the name of your city (e.g. `Frankfurt`). The integration will search the official database and present a list of stations to choose from.
-   **Direct Entry**: You can still enter a precise DS100 ID (e.g. `FF`) or EVA ID if you know it.
-   **Manual Override**: If a station is not found in the list, you can still proceed with your manual entry. A warning icon (⚠️) will indicate that the station name could not be verified, but the integration will attempt to fetch data for it anyway.

!!! info "Learn More"
    For detailed information about the station search feature, including search strategies and technical details, see the [Station Search Guide](station-search.md).

### 2. Data Source
Select the backend provider.
-   **IRIS-TTS**: The default and most reliable source for German stations. It provides high-frequency updates and quality notes.
-   **Regional/International**: Select providers like `ÖBB`, `SBB`, or regional networks when tracking trains outside Germany or on specific local lines not covered by the main DB IRIS system.

---

## 🛠️ Options Flow (Fine Tuning)

Once a sensor is created, click **Configure** on the integration card to access granular settings. These are categorized into meaningful groups.

### :material-clock-outline: General Options
-   **Update Interval**: Default is 3 minutes. Lowering this to 1 minute provides near-instant delay updates but increases API load.
-   **Offset (HH:MM)**: Shift the search window into the future.
    -   *Example*: Use `00:15` if you want to skip all trains leaving in the next 15 minutes because you haven't left the house yet.
-   **Number of Departures**: Controls how many entries are stored in the `departures` attribute. Increasing this (e.g. to 15) gives more historical/future visibility but increases state size.

### :material-filter-variant: Filter Options
*This is where the magic happens for commuters.*

!!! important "Delimiter Rule"
    **Always use a comma `,`** to separate multiple values in text fields.

-   **Platforms**: Enter a list of tracks you care about (e.g. `4, 5, 21`).
-   **Via Stations**: This is an **OR** filter.
    -   *Example*: `Köln, Düsseldorf`. The sensor will show any train that stops at EITHER Cologne OR Düsseldorf.
-   **Direction**: A substring search for the destination.
    -   *Example*: Entering `Paris` will catch `Paris Gare du Nord` and `Paris Est`.
-   **Excluded Directions**: Hide specific destinations. Useful for stations where many lines overlap.
-   **Exclude Cancelled Trains**:
    -   `True`: Cancelled trains vanish from your dashboard entirely.
    -   `False` (Default): Cancelled trains stay in the list (marked as `isCancelled: true`), allowing you to see *why* your commute is broken.

### :material-monitor-dashboard: Display Options
-   **Detailed Information**: Enables extra JSON metadata in attributes.
-   **Preferred Time Mode**:
    -   `Departure`: Default. Focuses on when the train leaves.
    -   `Arrival`: Useful if you are using the integration to track when someone is arriving at your station.
-   **Enable Text View**: A powerful feature for ePaper displays. It compiles the most important info into a single formatted string.
-   **Hide Low Delay**: Removes delay noise for delays less than 5 minutes.
-   **Show Occupancy**: Enables fetching of train occupancy data (load factor 1-4) if provided by the API.

### :material-flask: Advanced Options
-   **Custom API URL**: Essential if you are hosting your own [db-fakedisplay](https://github.com/derf/db-fakedisplay) instance.
-   **Deduplication**: Filters out redundant entries. Some data sources report the same train twice under different IDs; this keeps your UI clean.
-   **Keep Route**: Normally, only the destination is stored. Enable this to keep the **entire list of intermediate stops**.
-   **Past 60 Minutes**: Include trains that have already left in the last hour. Great for "What did I miss?" views.

---

### 🚀 Next Steps
Now that you have configured your sensors, check out the [Automation Cookbook](automations.md) for inspiration on how to use them!

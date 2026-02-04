# Configuration Options ⚙️

This page provides a detailed overview of all configuration options available during the initial setup and in the **Options Flow** (Integration settings).

---

## 🏗️ Initial Setup
When adding the integration for the first time, you are presented with the basic configuration.

| Option | Description | Example |
| :--- | :--- | :--- |
| **Station** | The name, DS100 code, or trip number of the station. | `Mainz Hbf` or `8000240` |
| **Data Source** | The backend used to fetch data. `IRIS-TTS` is official DB data. | `IRIS-TTS` |
| **Departures** | How many upcoming trains should be tracked by the sensor. | `5` |
| **Platforms** | (Optional) Limit to specific platforms (comma-separated). | `1, 4a` |
| **Via Stations** | (Optional) Only show trains stoping at these stations. | `Frankfurt` |
| **Direction** | (Optional) Only show trains heading toward this destination. | `Wiesbaden` |

---

## 🛠️ Options Flow (Settings)
Once installed, you can go to **Settings > Devices & Services > DB Infoscreen > Configure** to adjust settings. We've organized these into sub-menus for better navigation.

### 📋 General Settings
Basic update behavior and timing.

*   **Number of Upcoming Departures**: Updates the amount of tracked trains.
*   **Update Interval (minutes)**: How often the sensor polls the API. Default is 3 minutes.
*   **Offset Time**: Useful if you need 5 minutes to reach the platform. Enter `00:05` to ignore trains departing in the next 5 minutes.

### 🔍 Filter Settings
Refine which trains are shown.

*   **Platforms**: Filter by platform names.
*   **Via Stations**: Comma-separated list of stations the train must pass.
*   **Direction**: Only show trains with this final destination.
*   **Excluded Directions**: Hide trains heading toward these destinations.
*   **Ignored Train Types**: Multi-select list to hide `S-Bahn`, `Bus`, `ICE`, etc.
*   **Exclude Cancelled Trains**: If checked, cancelled departures are removed from the list entirely.

### 🖼️ Display Settings
Control how the data is presented in Home Assistant.

*   **Detailed Information**: Enables extra attributes for each departure (e.g., full route, wagon order).
*   **Enable Simplified Text View**: Provides a pre-formatted string for simple markdown cards.
*   **Display Mode (admode)**:
    *   `preferred departure`: Shows the planned time, but switches to actual time if delayed.
    *   `departure`: Always shows the departure time.
    *   `arrival`: Shows the arrival time (useful for tracking incoming trains).
*   **Favorite Trains**: A comma-separated list of train names (e.g., `ICE 123, RE 5`) to filter the departure board for commuters.
*   **Hide Low Delay**: Hide delays below 5 minutes to reduce visual clutter.

### ⚡ Advanced Settings
Technical settings and edge cases.

*   **Custom API URL**: If you self-host the backend, enter your URL here.
*   **Deduplicate Departures**: Removes "ghost" or duplicate entries often found in regional data.
*   **Keep Route Details**: Persists the full station list even if the API update is partial.
*   **Keep if Endstation**: Prevents the sensor from clearing data when reaching the final stop.
*   **Drop Late Trains**: Hide trains that have already "departed" logically but are still in the system due to delay.
*   **Include Past 60 Minutes**: Shows trains that departed in the last hour.
*   **Data Source**: Switch between IRIS (DB) and various regional HAFAS providers.

---

> [!TIP]
> Use the **"Finish and Save"** button in the main Options Menu to apply all changes you've made across different sub-menus at once.

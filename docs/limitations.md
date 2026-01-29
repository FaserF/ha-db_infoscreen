# Limitations ⚠️

While `ha-db_infoscreen` is a powerful tool, it operates within certain technical and administrative constraints. Understanding these will help you set realistic expectations for your dashboard.

---

## 🚦 API Rate Limits

The primary constraint for most users is the rate-limiting imposed by the public [Backend API](https://dbf.finalrewind.org/) (IRIS-TTS).

### Sensor Count
By default, the integration is configured to support a maximum of **30 sensors** per Home Assistant instance.
-   **Why?**: Every sensor performs its own API calls. A single station might result in multiple calls (IRIS + HAFAS + Quality). To prevent the public infrastructure from being overwhelmed (which could lead to a permanent IP ban for you), we enforce this limit.
-   **Host your own**: If you need more than 30 sensors, you **must** host your own instance of the [db-fakedisplay](https://github.com/derf/db-fakedisplay) backend.

### Update Frequency
The minimum update interval is **1 minute**.
-   **Why?**: Train data generally doesn't change every few seconds. Requesting data more frequently is counter-productive and puts unnecessary strain on the servers.

---

## 💾 Hardware & Database Constraints

Because this integration provides rich metadata (attributes), it can impact your Home Assistant host's resources.

### State Storage (The Recorder)
If you enable features like **"Detailed Information"** or **"Keep Route"**, the sensor attributes will contain large JSON objects.
-   **The Risk**: These attributes are saved to your Home Assistant database (`home-assistant_v2.db`) every time the sensor updates. Over weeks and months, this can lead to a massive database file, potentially slowing down backups or wearing out SD cards on Raspberry Pi devices.
-   **Recommendation**:
    -   Only enable "Keep Route" if you are actively using that data in a custom card.
    -   Consider excluding these sensors from your [Recorder configuration](https://www.home-assistant.io/integrations/recorder/#exclude).

### Memory Consumption
On low-end hardware (like the Raspberry Pi 3), having 30+ sensors with detailed route tracking enabled can consume a noticeable amount of RAM. Ensure your hardware is sized appropriately for your configuration.

---

## 🚂 Data Accuracy & Scope

The integration is only as good as the data it receives from the transport associations.

### "Ghost" Trains
Occasionally, the API might report a train that has been cancelled but the cancellation hasn't propagated through the various transit systems yet. This is an upstream issue and cannot be fixed within the integration.

### Coverage Gaps
While the backend supports dozens of providers, not all providers offer the same level of detail.
-   **IRIS-TTS**: Highly detailed (platform changes, quality notes).
-   **Some HAFAS backends**: May only provide basic arrival/departure times without platform info or delay reasons.

### Routing vs. Departures
This integration is **not a router**. It will not tell you which train to take to reach a specific destination if that involves changes. It only tells you what is leaving the current station.

??? info "How to replicate 'Routing'?"
    You can use the **Via Stations** filter to see only trains reaching your destination, but for complex trips with multiple transfers, you are better served by a dedicated routing integration or the official DB Navigator app.

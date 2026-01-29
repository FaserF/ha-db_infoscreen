# DB Infoscreen for Home Assistant 🚆

<div align="center">
  <img src="images/logo.png" alt="Logo" width="200px">

  <p>
    <a href="https://github.com/hacs/integration">
      <img src="https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge&logo=homeassistant" alt="HACS">
    </a>
    <a href="https://github.com/FaserF/ha-db_infoscreen/releases">
      <img src="https://img.shields.io/github/v/release/FaserF/ha-db_infoscreen?style=for-the-badge&logo=github&color=blue" alt="Integration Release">
    </a>
    <a href="https://github.com/derf/db-fakedisplay/releases">
      <img src="https://img.shields.io/badge/Backend-IRIS--TTS-orange?style=for-the-badge&logo=github" alt="Backend">
    </a>
  </p>
</div>

---

## 📊 Project Status

| Component | Status | Latest | Release Date |
| :--- | :--- | :--- | :--- |
| **Integration** | ![Active](https://img.shields.io/badge/status-active-success?style=flat-square) | ![GitHub release (latest by date)](https://img.shields.io/github/v/release/FaserF/ha-db_infoscreen?style=flat-square) | ![GitHub Release Date](https://img.shields.io/github/release-date/FaserF/ha-db_infoscreen?style=flat-square) |
| **Backend API** | ![Upstream](https://img.shields.io/badge/upstream-tracking-blue?style=flat-square) | ![Backend Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FFaserF%2Fha-db_infoscreen%2Fmain%2F.backend_version&query=%24.version&label=v&style=flat-square) | ![Stable](https://img.shields.io/badge/stable-yes-green?style=flat-square) |

---

## 🎯 Purpose & Motivation

**db-infoscreen** brings the experience of a **physical station departure board** into your smart home.

In the world of home automation, most "Public Transport" integrations focus on **Routing** (how to get from A to B). However, for many users—especially those living near a station—the more important question is:
> **"I know where I'm going, I just need to know if the next train is on time."**

This integration is designed for:
<div class="grid cards" markdown>

-   :material-tablet-dashboard: **Wall-mounted Dashboards**
    ---
    Perfect for hallway tablets or kitchen kiosks.

-   :material-mirror: **Magic Mirrors**
    ---
    At-a-glance information while getting ready.

-   :fontawesome-solid-train: **Commuter Checks**
    ---
    Quickly check if your S-Bahn is delayed before leaving the house.

</div>

---

## 📜 The Evolution: Legacy vs. Modernity

This project did not appear in a vacuum. It is the result of years of iteration and a fundamental shift in how we handle train data in Home Assistant.

### 🪦 The Legacy: `ha-deutschebahn` & `ha-bahnvorhersage`

If you have been a Home Assistant user in Germany for a while, you might remember [**ha-deutschebahn**](https://github.com/FaserF/ha-deutschebahn) or [**ha-bahnvorhersage**](https://github.com/FaserF/ha-bahnvorhersage).

**Why do these projects no longer exist/receive updates?**

1.  **Parsing/Scraping Nightmares**: These older integrations relied on "web scraping"—meaning they downloaded the HTML of public websites and tried to find the departure times in the code. Every time Deutsche Bahn changed a single line of CSS or HTML, the integration would break for everyone.
2.  **Unreliability**: Scraping is inherently fragile. It led to frequent "Unknown" states, broken sensors, and high maintenance overhead.
3.  **Complexity of Routing**: They tried to solve *routing* (finding connections between two points). This requires complex session management and handling of many edge cases that the public-facing websites weren't designed to provide via simple GET requests.
4.  **IP Bans**: Automated scraping is often detected and blocked by providers, leading to users getting temporarily banned from accessing train data.

### 🚀 The Solution: `ha-db_infoscreen`

`ha-db_infoscreen` was born from the realization that we needed an **API-first** approach. By leveraging the incredible [**db-fakedisplay**](https://github.com/derf/db-fakedisplay) project as a backend, we moved away from fragile scraping and towards structured data.

-   **Backend Stability**: We use the **IRIS-TTS** API—the same data source that powers actual platform displays at German stations.
-   **No Scraping**: We receive clean JSON data. No more broken sensors because of a website redesign.
-   **Focus on Departures**: By specializing in "Station Departure Boards", we provide the most reliable and information-dense experience for your dashboard.

---

## ❤️ Credits & Acknowledgments

This project is a bridge between the Home Assistant ecosystem and the wider open-source world.

!!! success "Project Hero: derf"
    A massive amount of credit goes to [**derf**](https://github.com/derf) for his tireless work on [**db-fakedisplay**](https://github.com/derf/db-fakedisplay).

    His backend project does the "heavy lifting": aggregating data from dozens of European transport associations (DB, ÖBB, SBB, and many more) and providing a unified, stable API. Without his work, this integration would not be possible. **Please consider starring his repository!**

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **Real-time Data** | Live delays, platform changes, and quality notes (e.g., "Train reversed"). |
| **Global Coverage** | Supports DB (Germany), ÖBB (Austria), SBB (Switzerland), and many local associations. |
| **Smart Filtering** | Exclude cancelled trains, filter by direction, or show only specific platforms. |
| **Deep Attributes** | Access route info, warnings, messages, train composition (`wagon_order`), and unique `trip_id`. |
| **Occupancy** | See how full the train is (1-4 scale) before it arrives. |
| **Station Search** | Integrated search prevents typos by letting you pick from official station names. |
| **ePaper Ready** | Built-in "Text View" mode for ESPHome/ePaper displays. |

---

## 🚀 Getting Started

[Install with HACS](installation.md){ .md-button .md-button--primary } [View Settings](configuration.md){ .md-button }

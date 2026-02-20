# Installation

You can install `ha-db_infoscreen` via **HACS** (recommended) or manually.

## Option 1: HACS (Recommended)

The easiest way to install and manage updates.

1.  Open your Home Assistant instance.
2.  Go to **HACS** > **Integrations**.
3.  Click the **+ Explore & Download Repositories** button.
4.  Search for `db-infoscreen`.
5.  Click **Download**.
6.  **Restart** Home Assistant.

[![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-db_infoscreen&category=integration)

!!! tip "Why HACS?"
    HACS handles updates for you, ensuring you always have the latest fixes (like API URL changes) and features.

## Option 2: Manual Installation

If you prefer not to use HACS:

1.  Download the latest release zip from the [GitHub Releases page](https://github.com/FaserF/ha-db_infoscreen/releases).
2.  Unzip the file.
3.  Copy the `db_infoscreen` directory into your Home Assistant's `custom_components` directory:
    ```path
    /config/custom_components/db_infoscreen
    ```
4.  **Restart** Home Assistant.

---

## Installing Beta Releases

Beta releases allow you to test new features or fixes before they are officially released.

### Via HACS

As of **February 2026**, HACS makes switching to beta versions very simple:

1.  Open your Home Assistant instance and navigate to **HACS**.
2.  Search for or find **db-infoscreen** in your downloaded integrations.
3.  Click on the integration to open its details page.
4.  Click the **three dots (overflow menu)** in the top right corner.
5.  Select **Redownload** (or **Download**).
6.  In the dialog that appears, enable the toggle **Show beta versions**.
7.  Select the desired beta version from the dropdown menu.
8.  Click **Download**.
9.  **Restart** Home Assistant when prompted.

### Manual Beta Installation

1.  Navigate to the [GitHub Releases page](https://github.com/FaserF/ha-db_infoscreen/releases).
2.  Look for versions marked with a **Pre-release** badge.
3.  Download the `Source code (zip)` for that version.
4.  Follow the standard **Manual Installation** steps above (extract and copy the `custom_components/db_infoscreen` folder).
5.  **Restart** Home Assistant.

---

## Post-Installation

Once installed (and after a restart), you need to add the integration to your instance:

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **+ Add Integration**.
3.  Search for **DB Infoscreen**.
4.  Follow the setup wizard to configure your first station.

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=db_infoscreen)

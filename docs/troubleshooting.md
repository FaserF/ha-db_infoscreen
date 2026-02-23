# Troubleshooting & Support 🛠️

If things aren't working as expected, follow this guide to identify and resolve the issue.

---

## 🔍 Common Issues

### "No Data" or `Unavailable`

-   **Check Logs**: Go to **Settings > System > Logs**. Look for errors related to `db_infoscreen`.

-   **API Limit**: Are you using more than 30 sensors? You might be rate-limited by the public API.

-   **Station Name**: Ensure the station name is spelled correctly or use the DS100 ID.

### Values are not persisting
If you change a setting in the "Options" menu and it doesn't seem to take effect:

-   **Fixed (v2026.1.1+)**: Ensure you are using **commas** `,` to separate multiple stations or platforms. Old versions used pipes `|`, which are no longer supported in the UI.

### Delays are missing

The availability of real-time delay data depends on the **Data Source**.

-   **IRIS-TTS** provides the best live data for Germany.

-   Regional HAFAS sources might only update delays every few minutes or not at all for certain train types.

---

## 📝 Debug Logging

To help developers diagnose complex issues, please provide debug logs.

1.  Add the following to your `configuration.yaml`:
    ```yaml
    logger:
      default: info
      logs:
        custom_components.db_infoscreen: debug
    ```
2.  Restart Home Assistant.
3.  Observe the issues and copy the relevant logs from the System Logs.

---

## 💬 Community & Support

-   **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/FaserF/ha-db_infoscreen/issues).
-   **Discussions**: Check the [GitHub Discussions](https://github.com/FaserF/ha-db_infoscreen/discussions) (if enabled) or community forums for setup help.

!!! help "Need Help?"
    When opening an issue, please always include your **Diagnostic Information** (available on the Integration entry via the three-dot menu).

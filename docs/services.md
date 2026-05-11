# Services 🛠️

The DB Infoscreen integration historically only provided entities. With the latest update, we introduce services to enable more interactive features like active train monitoring.

---

## `watch_train` 🚂

This service allows you to monitor a specific train (today) and receive push notifications when something changes. This is perfect for when you are at home and want to be alerted if your specific commute train is delayed, cancelled, or changes platforms.

### Service Data

| Field | Type | Description |
| :--- | :--- | :--- |
| `train_id` | string | **Required**. The Train number (e.g., `ICE 123`) or Trip ID of the train to monitor. |
| `notify_service` | string | **Required**. The notification service to call (e.g., `notify.mobile_app_iphone`). |
| `delay_threshold` | integer | **Optional**. Minimum delay in minutes to trigger a notification (Default: 5). |
| `notify_on_platform_change` | boolean | **Optional**. Notify if the train switches platforms (Default: true). |
| `notify_on_cancellation` | boolean | **Optional**. Notify if the train is cancelled (Default: true). |

### Example Usage

You can call this service from an automation, a dashboard button, or via the Developer Tools.

**Call from Automation:**
```yaml
service: db_infoscreen.watch_train
data:
  train_id: "ICE 578"
  notify_service: "notify.mobile_app_iphone"
  delay_threshold: 3
```

**What it does:**

1. Adds the train to a temporary "watchlist".

2. On every data update, it checks the status of this specific train.

3. If criteria are met, it sends a notification with details.

4. Auto-cleans up once the train is no longer in the departure list.

---

## `track_connection` 🔄

This service extends the monitoring capability by tracking the connecting train at a transfer station.

### Service Data

| Field | Type | Description |
| :--- | :--- | :--- |
| `my_train_id` | string | **Required**. The ID or Number of your current train (e.g., `ICE 123`). |
| `change_station` | string | **Required**. The station where you change trains (e.g., `München Hbf`). |
| `next_train_id` | string | **Required**. The ID or Number of the connecting train (e.g., `RE 456`). |

### Example Usage

**Call from Automation:**
```yaml
service: db_infoscreen.track_connection
data:
  my_train_id: "ICE 123"
  change_station: "München Hbf"
  next_train_id: "RE 456"
```

**What it does:**

- Tracks the status of `RE 456` potentially at a different station.

- Notifies you if the connection becomes risky due to delays.

---

## `set_paused` ⏸️

Toggles periodic updates for one or more stations. This is useful for "Smart Pausing" when you are not at home or during the night to save API queries.

### Service Data

| Field | Type | Description |
| :--- | :--- | :--- |
| `paused` | boolean | **Required**. Whether to pause (`true`) or resume (`false`) updates. |
| `station` | string | **Optional**. The station name to apply the paused state to. |
| `entity_id` / `device_id` | target | **Optional**. The Home Assistant entities or devices to target. |

### Example Usage

```yaml
service: db_infoscreen.set_paused
target:
  entity_id: sensor.frankfurt_hbf
data:
  paused: true
```

---

## `set_offset` ⏱️

Dynamically overrides the default time offset for departures temporarily. This can be used if you know you are walking slower today or if you want to see trains further in the future for a short period.

### Service Data

| Field | Type | Description |
| :--- | :--- | :--- |
| `offset` | string | **Required**. The new time offset in format `HH:MM` (e.g. `00:05`). |
| `station` | string | **Optional**. The station name to apply the offset to. |
| `entity_id` / `device_id` | target | **Optional**. The Home Assistant entities or devices to target. |

### Example Usage

```yaml
service: db_infoscreen.set_offset
target:
  device_id: 1234567890abcdef
data:
  offset: "00:15"
```

---

!!! tip "Tip: Targeting Stations"
    You can target stations by their **Station Name** (text), by selecting their **Entities**, or by selecting the **Device**. If you leave the target/station blank, the service will apply to **all** configured stations.

!!! tip "Tip: Track from Dashboard"
    You can use a `button` card in Lovelace to start watching your next train with a single tap before you leave the house!

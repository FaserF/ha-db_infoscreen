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

!!! tip "Tip: Track from Dashboard"
    You can use a `button` card in Lovelace to start watching your next train with a single tap before you leave the house!

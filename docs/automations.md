# Automation Cookbook 🤖

Unlock the full power of `ha-db_infoscreen` with these automation examples. Copy and paste them into your `automations.yaml` or use them as inspiration!

---

## 🚨 Critical Commuter Alerts

### 1. Platform Change Notification
Get notified immediately if your train moves to a different track.

```yaml
alias: "Train: Platform Change Alert"
trigger:
  - platform: template
    value_template: >
      {% set next_train = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
      {{ next_train.changed_platform is defined and next_train.changed_platform }}
action:
  - service: notify.mobile_app_iphone
    data:
      title: "📢 Platform Change!"
      message: >
        Your train {{ state_attr('sensor.frankfurt_hbf', 'departures')[0].train }}
        is now departing from Platform {{ state_attr('sensor.frankfurt_hbf', 'departures')[0].platform }}!
        (Scheduled: {{ state_attr('sensor.frankfurt_hbf', 'departures')[0].scheduledPlatform }})
```

### 2. High Occupancy Warning
Warn if the next train is overcrowded so you can wait for the next one.

```yaml
alias: "Train: Overcrowding Warning"
trigger:
  - platform: template
    value_template: >
      {% set next = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
      {{ next.occupancy is defined and next.occupancy == 4 }}
action:
  - service: notify.mobile_app_iphone
    data:
      title: "⚠️ High Occupancy"
      message: "The next train is exceptionally full (Level 4). Consider waiting for the next connection."
```

### 3. Cancelled Train Alert
Don't rush to the station if the train isn't coming.

```yaml
alias: "Train: Cancellation Alert"
trigger:
  - platform: template
    value_template: >
      {% set next = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
      {{ next.isCancelled is defined and next.isCancelled }}
action:
  - service: notify.alexa_media
    data:
      target: media_player.kitchen_echo
      message: "Attention! The next train towards {{ state_attr('sensor.frankfurt_hbf', 'departures')[0].destination }} has been cancelled."
      data:
        type: tts
```

---

## ☕ Comfort & Facilities

### 4. No WiFi / Bistro Closed
Know before you go if you can work or grab a coffee.

```yaml
alias: "Train: Service Disruption"
trigger:
  - platform: template
    value_template: >
      {% set next = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
      {{ next.facilities is defined and (next.facilities.wifi == false or next.facilities.bistro == false) }}
action:
  - service: notify.mobile_app_iphone
    data:
      title: "☕ Service Update"
      message: >
        Heads up:
        {% if state_attr('sensor.frankfurt_hbf', 'departures')[0].facilities.wifi == false %}❌ WiFi is broken.{% endif %}
        {% if state_attr('sensor.frankfurt_hbf', 'departures')[0].facilities.bistro == false %}❌ Bistro is closed.{% endif %}
```

### 5. Sector Information (Stop Position)
Tell you exactly where to stand on the platform (e.g., Section A-C).

```yaml
alias: "Train: Platform Sector Info"
trigger:
  - platform: state
    entity_id: sensor.frankfurt_hbf
    attribute: departures
action:
  - service: notify.mobile_app_iphone
    data:
      message: >
        Next train stops in sectors: {{ state_attr('sensor.frankfurt_hbf', 'departures')[0].platform_sectors }}
```

---

## 🧠 Advanced Logic

### 6. Track Specific Trip (Trip-ID)
Track a specific train run regardless of delay. Useful if you are meeting someone.

```yaml
alias: "Train: Track ICE 279"
trigger:
  - platform: template
    value_template: >
      {% set trains = state_attr('sensor.frankfurt_hbf', 'departures') %}
      {{ trains | selectattr('trip_id', 'eq', '123456789') | list | count > 0 }}
action:
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.guest_arrival
    data:
      timestamp: >
        {% set train = state_attr('sensor.frankfurt_hbf', 'departures') | selectattr('trip_id', 'eq', '123456789') | first %}
        {{ as_timestamp(train.scheduledArrival) + (train.delayArrival | int * 60) }}
```

### 7. "Should I Run?" Light
Turn a light RED if delay is < 5 min (run!), YELLOW if < 10 min, GREEN if > 10 min.

```yaml
alias: "Train: Traffic Light"
trigger:
  - platform: state
    entity_id: sensor.frankfurt_hbf
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
    data:
      rgb_color: >
        {% set delay = state_attr('sensor.frankfurt_hbf', 'departures')[0].delayDeparture | int %}
        {% if delay < 5 %}
          [255, 0, 0]  # Red (Run!)
        {% elif delay < 10 %}
          [255, 255, 0] # Yellow
        {% else %}
          [0, 255, 0] # Green (Relax)
        {% endif %}
```

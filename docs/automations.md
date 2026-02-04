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
      {% set trains = state_attr('sensor.frankfurt_hbf', 'departures') %}
      {% if trains %}
        {% set next_train = trains[0] %}
        {{ next_train.changed_platform is defined and next_train.changed_platform }}
      {% else %}
        false
      {% endif %}
action:
  - service: notify.mobile_app_iphone
    data:
      title: "📢 Platform Change!"
      message: >
        {% set trains = state_attr('sensor.frankfurt_hbf', 'departures') %}
        {% if trains %}
          Your train {{ trains[0].train }}
          is now departing from Platform {{ trains[0].platform }}!
          (Scheduled: {{ trains[0].scheduledPlatform }})
        {% else %}
          Check DB App!
        {% endif %}
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
      rgb_color: >
        {% set trains = state_attr('sensor.frankfurt_hbf', 'departures') %}
        {% if trains %}
          {% set delay = trains[0].delayDeparture | int %}
          {% if delay < 5 %}
            [255, 0, 0]  # Red (Run!)
          {% elif delay < 10 %}
            [255, 255, 0] # Yellow
          {% else %}
            [0, 255, 0] # Green (Relax)
          {% endif %}
        {% else %}
          [255, 255, 255] # White (No Info)
        {% endif %}
        {% elif delay < 10 %}
          [255, 255, 0] # Yellow
        {% else %}
          [0, 255, 0] # Green (Relax)
        {% endif %}
```

---

## 🌍 Multi-Source & Complex Configurations

### 8. Regional Train Filter (e.g., ÖBB / SBB)
If you use the `ÖBB` data source, you might want to filter simply by line name.

```yaml
alias: "Train: Filter for Railjet (RJX)"
trigger:
  - platform: template
    value_template: >
      {% set trains = state_attr('sensor.wien_hbf', 'departures') %}
      {{ trains | selectattr('train', 'search', 'RJX') | list | count > 0 }}
action:
  - service: notify.mobile_app_iphone
    data:
      message: "Railjet Express is available!"
```

### 9. "Via" Station Priority
Sometimes two trains go to the same destination but one takes a faster or specific route (e.g., via Airport).

```yaml
alias: "Train: Via Airport Alert"
trigger:
  - platform: template
    value_template: >
      {% set next = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
      {{ 'Frankfurt Flughafen' in next.via }}
action:
  - service: notify.mobile_app_iphone
    data:
      title: "✈️ Airport Connection"
      message: "The next train takes the Airport route. Perfect for your flight!"
```

### 10. Dashboard Card Swipe (Conditional)
Hide your departure card if no trains are running (e.g., at night), keeping your dashboard clean.

```yaml
type: conditional
conditions:
  - entity: sensor.frankfurt_hbf
    state_not: "unavailable"
  - entity: sensor.frankfurt_hbf
    state_not: "unknown"
card:
  type: markdown
  content: >
    ## 🚆 Departures
    {% for t in state_attr('sensor.frankfurt_hbf', 'departures')[:3] %}
    - **{{ t.time }}** {{ t.train }} -> {{ t.destination }} (+{{ t.delayDeparture }})
    {% endfor %}
```

### 11. Smart Alarm Adjustment
Use the `android.intent` command to set your phone alarm 30 mins before the train leaves.

```yaml
alias: "Train: Set Wake Up Alarm"
trigger:
  - platform: time
    at: "06:00:00"
action:
  - service: notify.mobile_app_android
    data:
      message: "command_activity"
      data:
        intent_package_name: "com.google.android.deskclock"
        intent_action: "android.intent.action.SET_ALARM"
        intent_extras: >
          {% set next = state_attr('sensor.frankfurt_hbf', 'departures') | first %}
          {% set dep_time = as_timestamp(next.scheduledDeparture) %}
          {% set wake_up = dep_time - (30 * 60) %}
          hour:{{ wake_up | timestamp_custom('%H') }},minutes:{{ wake_up | timestamp_custom('%M') }},skip_ui:true
```

---

## 🎨 Lovelace Dashboard Examples

### 12. Premium Departure Board Card
A beautiful, dynamic departure board using a Markdown card. Shows delays, platform changes, and wagon order.

```yaml
type: markdown
title: 🚆 Departures
content: >
  {% set departures = state_attr('sensor.frankfurt_hbf', 'next_departures') or [] %}
  {% if departures | length > 0 %}
  | Time | Train | Destination | Platform |
  |:-----|:------|:------------|:---------|
  {% for dep in departures[:5] %}
  {% set delay = dep.delayDeparture | int(0) %}
  {% set time_str = dep.scheduledDeparture or dep.scheduledArrival or '?' %}
  {% set delay_str = ' +' ~ delay if delay > 0 else '' %}
  {% set platform = dep.platform or '?' %}
  {% set changed = '⚠️ ' if dep.changed_platform else '' %}
  {% set cancelled = '~~' if dep.isCancelled else '' %}
  | {{ cancelled }}{{ time_str }}{{ delay_str }}{{ cancelled }} | {{ dep.train }} | {{ dep.destination }} | {{ changed }}{{ platform }} |
  {% endfor %}
  {% else %}
  *No departures available*
  {% endif %}
```

### 13. Compact Next Train Widget
A minimal card showing just the next train with key info.

```yaml
type: custom:button-card
entity: sensor.frankfurt_hbf
show_name: false
show_icon: true
icon: mdi:train
styles:
  card:
    - padding: 16px
    - background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)
  icon:
    - color: '#00d4ff'
custom_fields:
  train: >
    [[[ return (entity.attributes.next_departures || [])[0]?.train || '?' ]]]
  time: >
    [[[
      const dep = (entity.attributes.next_departures || [])[0];
      const delay = dep?.delayDeparture || 0;
      const time = dep?.scheduledDeparture || '?';
      return delay > 0 ? `${time} +${delay}` : time;
    ]]]
  dest: >
    [[[ return (entity.attributes.next_departures || [])[0]?.destination || '?' ]]]
```

### 14. Wagon Order Display
Show the wagon order summary for the next ICE/IC train.

```yaml
type: conditional
conditions:
  - condition: template
    value_template: >
      {{ state_attr('sensor.frankfurt_hbf', 'next_departures')[0].wagon_order_html is defined }}
card:
  type: markdown
  content: >
    ### 🚃 Wagon Order
    {{ state_attr('sensor.frankfurt_hbf', 'next_departures')[0].wagon_order_html | safe }}
```

### 15. Alternative Connections Card
Show backup trains if you miss the first one.

```yaml
type: markdown
title: 🔄 Alternative Connections
content: >
  {% set first = state_attr('sensor.frankfurt_hbf', 'next_departures')[0] %}
  {% if first.alternative_connections is defined %}
  If you miss **{{ first.train }}**, you can also take:
  {% for alt in first.alternative_connections %}
  - {{ alt.train }} at {{ alt.scheduledDeparture }} (Pl. {{ alt.platform or '?' }})
  {% endfor %}
  {% else %}
  *No alternative connections available.*
  {% endif %}
```

### 16. Trip Watchdog Status
Display the delay status at the previous station.

```yaml
type: entity
entity: sensor.frankfurt_hbf_trip_watchdog
name: Previous Station
icon: mdi:eye-check
```

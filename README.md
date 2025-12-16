[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# DB Infoscreen Home Assistant Sensor 🚆

The `db-infoscreen` sensor provides **departure times** and detailed train information for a given station. It aggregates data from multiple sources (primarily **Deutsche Bahn IRIS-TTS**) to give you a comprehensive departure board directly in Home Assistant.

<img src="images/logo.png" alt="Logo" width="300px">
<img src="images/sensor.png" alt="Station Sensor" width="300px">

## Features ✨

- ** comprehensive Departure Board**: Next departures, delays, platforms.
- **Wide Coverage**: Supports DB and many local transport associations (via HAFAS/EFA).
- **Highly Configurable**: Filter by direction, train type, and more.
- **Detailed Attributes**: Route info, messages, train composition details.

## Installation 🛠️

### 1. Using HACS (Recommended)

This integration is an **official HACS Integration**.

1.  Open HACS.
2.  Search for "db-infoscreen".
3.  Click **Download**.

[![Open your Home Assistant instance to install this integration from the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-db_infoscreen&category=integration)

> [!TIP]
> HACS ensures you stay up-to-date with the latest API changes.

### 2. Manual Installation

1.  Download the latest [Release](https://github.com/FaserF/ha-db_infoscreen/releases/latest).
2.  Extract the ZIP file.
3.  Copy the `db_infoscreen` folder to `<config>/custom_components/`.

## Configuration ⚙️

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration**.
3.  Search for "db-infoscreen".

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=db_infoscreen)

### Configuration Variables

| Key                      | Type    | Required | Default | Description |
|--------------------------|---------|----------|---------|-------------|
| `station`               | string  | Yes      | -       | The name of the station, Trip number or DS100 ID to be tracked. [This page](https://ds100.frankfurtium.de/dumps/orte_de.html) may help in finding the DS100 ID to avoid issues with special chars (e.g., 'IMH' for 'München Hbf (Sp)'). |
| `next_departures`       | int     | No       | 4       | Number of upcoming departures to display. Please note that there may be displayed less than your number, due to [storage limitations](https://github.com/FaserF/ha-db_infoscreen/issues/22). |
| `update_interval`       | int     | No       | 3       | Time interval (in minutes) to fetch updated departure data. Minimum: 1 minute. |
| `hide_low_delay`        | boolean | No       | False   | Hide departures with a delay of less than 5 minutes. |
| `drop_late_trains`      | boolean | No       | False   | Hide past departures that would still be delayed. |
| `deduplicate_departures`      | boolean | No       | False   | Filter out similar "duplicate" departures. |
| `detailed`             | boolean | No       | False   | Show additional details about departures. For example: messages, id, stop_id_num, stateless, key, mot |
| `past_60_minutes`      | boolean | No       | False   | Show departures from the past 60 minutes. |
| `keep_route`           | boolean | No       | False   | Keep route (stopover) details (all train stations on train route). |
| `keep_endstation`      | boolean | No       | False   | Keep departure if station is also endstation. |
| `custom_api_url`       | string  | No       | -       | Use a custom API URL instead of the default one. |
| `data_source`          | string  | No       | IRIS-TTS | Choose the data source for fetching departure information. More details can be found below at Data Sources. |
| `offset`              | string  | No       | 00:00   | Time offset for departure search (HH:MM or HH:MM:SS). |
| `admode`              | string  | No       | departure preferred | Defines whether to display departure or arrival times. |
| `platforms`           | string  | No       | -       | Filter by specific platform(s) (comma-separated). |
| `via_stations`        | string  | No       | -       | Filter by stations where the train must pass through. |
| `direction`           | string  | No       | -       | Filter departures by direction text. Useful for APIs that do not provide 'via' stations but a 'direction' (may not work for all data sources, e.g., IRIS-TTS). |
| `ignored_train_types` | list    | No       | []      | List of train types to ignore (may not work for all data sources, e.g., VMT). |

#### Warnings and Limitations

- **Sensor limits:** You are limited to adding 30 sensors, if you are not using a custom_api_url. This is due to backend limitations, see [here](https://dbf.finalrewind.org/) under "API".
- **Storage Limitations:** Certain configurations (e.g., `detailed`, `keep_route`, or many `next_departures`) may quickly lead to reaching storage limitations. See [issue #22](https://github.com/FaserF/ha-db_infoscreen/issues/22) for details.
- **Data Accuracy:** The accuracy of the departure information depends on the selected `data_source`. Some sources may provide outdated or incomplete data.
- **Update Interval:** The minimum `update_interval` is 1 minute. A lower interval may cause high API usage and lead to throttling or bans. This is due to backend limitations, see [here](https://dbf.finalrewind.org/) under "API".
- **Custom API URL:** If using `custom_api_url`, ensure that the API follows the expected response format to avoid errors.


#### Data Sources
Supported are only available [Backend Sources from DBF](https://dbf.finalrewind.org/_backend). There is no way for me to support other sources than that. The mentioned sources there are all using HAFAS or EFA. If you are missing a source that uses HAFAS or EFA, you can create a feature request at [a db-infoscreen - (formerly db-fakedisplay)](https://github.com/derf/db-fakedisplay/tree/main).


- **data_source** (optional): Choose the data source for fetching departure information.
  - The integration supports fetching departure data from various data sources, including:
    - IRIS-TTS (DB) – Deutsche Bahn AG (db.de) (default and used by most)
    - Germany (DE)
      - AVV – Aachener Verkehrsverbund Nordrhein-Westfalen (avv.de)
      - AVV – Augsburger Verkehrs- und Tarifverbund (avv-augsburg.de)
      - BEG - Bayrische Eisenbahngesellschaft (beg.bahnland-bayern.de)
      - BSVG – Braunschweiger Verkehrs-GmbH
      - BVG – Berliner Verkehrsbetriebe Berlin, Brandenburg (bvg.de)
      - bwegt - Personennahverkehr in Baden-Württemberg (ehem. 3-Löwen-Takt)
      - DING – Donau-Iller Nahverkehrsverbund
      - IRIS-TTS – Deutsche Bahn (Standard)
      - KVB – Kölner Verkehrs-Betriebe (kvb.koeln)
      - KVV – Karlsruher Verkehrsverbund Baden-Württemberg
      - MVV – Münchener Verkehrs- und Tarifverbund Bayern
      - NAHSH – Nahverkehrsverbund Schleswig-Holstein (nah.sh)
      - NASA – Personennahverkehr in Sachsen-Anhalt (nasa.de)
      - NVBW – Nahverkehrsgesellschaft Baden-Württemberg
      - NVV – Nordhessischer Verkehrsverbund Hessen (nvv.de)
      - NWL – Nahverkehr Westfalen-Lippe
      - RMV – Rhein-Main-Verkehrsverbund
      - Rolph – DB Rolph
      - RSAG – Rostocker Straßenbahn Mecklenburg-Vorpommern (rsag-online.de)
      - RVV – Regensburger Verkehrsverbund
      - SaarVV – Saarländischer Verkehrsverbund DE-SL (saarvv.de)
      - VAG - Freiburger Verkehrs AG
      - VBB – Verkehrsverbund Berlin-Brandenburg (vbb.de)
      - VBN – Verkehrsverbund Bremen/Niedersachsen (vbn.de)
      - VGN – Verkehrsverbund Großraum Nürnberg Bayern
      - VMT – Verkehrsverbund Mittelthüringen Thüringen (vmt-thueringen.de)
      - VMV – Verkehrsgesellschaft Mecklenburg-Vorpommern
      - VOS – Verkehrsgemeinschaft Osnabrück (vos.info)
      - VVO – Verkehrsverbund Oberelbe
      - VRN – Verkehrsverbund Rhein-Neckar
      - VRN2 – Verkehrsverbund Rhein-Neckar
      - VRR – Verkehrsverbund Rhein-Ruhr
      - VRR2 – Verkehrsverbund Rhein-Ruhr
      - VRR3 – Verkehrsverbund Rhein-Ruhr
      - VVS – Verkehrs- und Tarifverbund Stuttgart Baden-Württemberg
    - Austria (AT)
      - LinzAG – Linz AG
      - ÖBB – Österreichische Bundesbahnen
      - STV – Steirischer Verkehrsverbund (verbundlinie.at)
    - Switzerland (CH)
      - BLS – BLS AG Kanton Bern, Kanton Luzern (bls.ch)
      - TPG – Transports publics genevois (tpg.ch)
      - ZVV – Züricher Verkehrsverbund Kanton Zürich (zvv.ch)
    - Denmark (DK)
      - DSB – Rejseplanen (rejseplanen.dk)
    - Ireland (IE)
      - IE – Iarnród Éireann Irland, Nordirland (irishrail.ie)
    - Luxembourg (LU)
      - mobiliteit – mobilitéits zentral (mobiliteit.lu)
    - Poland (PL)
      - PKP - Polskie Koleje Państwowe
    - Sweden (SE)
      - Resrobot – Resrobot
    - USA (US)
      - BART – Bay Area Rapid Transit California (bart.gov)
      - CMTA – Capital Metro Austin Public Transport Texas (capmetro.org)
  - Some stations can be searched via "IRIS-TTS" but need hafas=1 for data retrival, f.e. "Frankenforst Kippekausen, Bergisch Gladbach", choose `hafas=1` in the list to archive this. [GitHub issue about this](https://github.com/FaserF/ha-db_infoscreen/issues/8)

### Migrating from [ha-deutschebahn](https://github.com/FaserF/ha-deutschebahn)

Migration from `ha-deutschebahn` to `ha-db_infoscreen` is not directly possible because the two integrations use different API sources and data structures. The old `ha-deutschebahn` API supported start and destination stations directly, which the new `db_infoscreen` API cannot fully replicate. However, you can still achieve a similar experience with a few workarounds:

#### Options to Achieve a "Start to Destination" Experience:

1. **Use the `platforms` Parameter**
   You can display only one direction by filtering for specific platforms. For example, show only trains from Munich to Augsburg, and then filter by specific end stations on the way.

2. **Use Two Sensors**
   To simulate a fixed start-to-destination route, create two sensors for the same station but with different `via_stations`. This will allow you to simulate the direction from the start station to the destination.

---

#### Key Options for "Start to Destination" (Migration)

- **Platform Filter (`platforms`)**:
  Use this parameter to restrict departures to specific platforms. This can help narrow down the direction you want to track.

- **Via Stations (`via_stations`)**:
  To simulate a specific direction, use `via_stations` to filter trains passing through certain intermediate stations.

- **Use Two Sensors**:
  If you want to filter departures in a single direction (for example, from Munich to Augsburg), use two sensors with different `via_stations` configurations.

---

#### Further Information

All other features of the old `ha-deutschebahn` integration have been ported to `ha-db_infoscreen`. For further discussion, check out the [discussion on GitHub](https://github.com/FaserF/ha-db_infoscreen/issues/4).
You can also check out some examples in Accessing the data.


## Accessing the data

### Automations
```yaml
automation:
  - alias: Notify Train Delay
    description: "Notify when the next train is delayed by more than 10 minutes."
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.station_departures', 'next_departures')[0]['delayArrival'] | int > 10 }}"
    action:
      - service: notify.notify
        data:
          message: >
            The next train to {{ state_attr('sensor.station_departures', 'next_departures')[0]['destination'] }}
            is delayed by {{ state_attr('sensor.station_departures', 'next_departures')[0]['delayArrival'] }} minutes.
    mode: single
```

### Custom sensor
Add a custom sensor in your configuration.yaml

```yaml
sensor:
  - platform: template
    sensors:
      next_train_departure:
        friendly_name: "Next Train Departure"
        value_template: >
          {{ state_attr('sensor.station_departures', 'next_departures')[0]['scheduledArrival'] }}
        icon_template: mdi:train
```

#### Community submit by [kRew94](https://github.com/kRew94) (Improved by [kaffeetrinker71](https://github.com/FaserF/ha-db_infoscreen/issues/4#issuecomment-2611684018))
This is a template sensor which gives the information for a destination in the format "HH:MM +DELAY":

```yaml
{%- set number = 0 -%}
{%- set connections = state_attr('sensor.uelzen_departures_via_hannover_hbf', 'next_departures') | selectattr('isCancelled', 'equalto', 0) | list -%}
{% if connections is not none and connections | length > number %}
  {% set connection = connections[number] %}
  {% set product = connection.train %}
  {% set departure = connection.scheduledDeparture %}
  {% set delay = connection.delayDeparture | int %}
  {{ product }} um {{ departure }}{% if delay > 0 %} +{{ delay }}{% endif %}
{% else %}
  No data
{% endif %}
```
The result looks like this: "ICE 2935 um 07:15"

### YAML Snippets
There are some examples that can be used within automations or custom sensors.

#### Community submit by [Kanecaine](https://github.com/Kanecaine)
I have a sensor for Berlin Central Station and would now like to know which connections there are to Leipzig and should give you the following output:
IC 495 um 22:28 +1.

[More informations](https://github.com/FaserF/ha-db_infoscreen/issues/4#issuecomment-2605743834).

```yaml
{%- set my_station = "Berlin Hbf" -%}
{%- set target = "Leipzig Hbf" -%}
{%- set number = 0 -%}
{%- set connections = state_attr('sensor.berlin_hbf_departures', 'next_departures') | default([]) | selectattr('isCancelled', 'equalto', 0) -%}
{%- set valid_connections = namespace(connections=[]) -%}
{%- for connection in connections -%}
  {%- set route = connection.route | default([]) | selectattr('name', 'defined') | map(attribute='name') | list -%}
  {%- if my_station in route and target in route and route.index(target) > route.index(my_station) -%}
    {%- set valid_connections.connections = valid_connections.connections + [connection] -%}
  {%- endif -%}
{%- endfor -%}

{%- if valid_connections.connections | length > number -%}
  {%- set connection = valid_connections.connections[number] -%}
  {%- set product_raw = connection.train | default('Unknown') -%}
  {%- set product = product_raw | regex_replace('^(Bus).*|^([A-Z]{2})\\s?\\d*', '\\1\\2') | replace("S ", "S") -%}
  {%- set departure = connection.scheduledDeparture | default('--') -%}
  {%- set delay = connection.delayDeparture | default(0) | int -%}
  {{ product }} {{ departure }}{% if delay > 0 %} +{{ delay }}{% endif %}
{%- else -%}
  --
{%- endif -%}
```

### JSON Format
The API returns data in the following json format usually:

```json
{
  "departures": [
    {
      "scheduledArrival": "08:08",
      "destination": "München-Pasing",
      "train": "S 4",
      "platform": "4",
      "delayArrival": 18,
      "messages": {
        "delay": [
          {"text": "delay of a train ahead", "timestamp": "2025-01-21T07:53:00"}
        ]
      }
    }
  ]
}
```

There are some differences depending on the stations, for example:
```json
{
  "departures": [
    {
      "delay": 0,
      "destination": "Bensberg, Bergisch Gladbach",
      "direction": "Bensberg, Bergisch Gladbach",
      "isCancelled": null,
      "messages": [],
      "platform": null,
      "route": [],
      "scheduledPlatform": null,
      "scheduledTime": 1737619740,
      "time": 1737619740,
      "train": "STR 1",
      "trainNumber": "54726",
      "via": []
    }
  ]
}
```

### Lovelace Custom Cards
There are some lovelace custom cards, which bringt you a better overview on your dashboard. Be sure to check them out.

#### ha-departureCard
Check out the card [here](https://github.com/BagelBeef/ha-departureCard/).

#### ha-public-transport-connection-card
This is currently Work-in-Progress by the maintainer, more informations are [here](https://github.com/silviokennecke/ha-public-transport-connection-card/issues/22).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you'd like to help improve this integration.

## Bug reporting
Open an issue over at [github issues](https://github.com/FaserF/ha-db_infoscreen/issues). Please prefer sending over a log with debugging enabled.

To enable debugging enter the following in your configuration.yaml

```yaml
logger:
    logs:
        custom_components.db_infoscreen: debug
```

You can then find the log in the HA settings -> System -> Logs -> Enter "db-infoscreen" in the search bar -> "Load full logs"

## Thanks to
The data is coming from the [dbf.finalrewind.org](https://dbf.finalrewind.org/) website (if no custom API Server is specified).
The backend data is coming from [a db-infoscreen - (formerly db-fakedisplay) server](https://github.com/derf/db-fakedisplay/tree/main) - with a huge thanks to [derf](https://github.com/derf) for this great project!

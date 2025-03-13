[![hacs_badge](https://img.shields.io/badge/HACS-CUSTOM-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# db-infoscreen Homeassistant Sensor
The `db-infoscreen` sensor will give you the departure time of the next trains for the given station, containing many more attribute informations. It aims to aggregate departure and train data from different sources and combine them in a useful (and user-friendly) manner. It is intended both for a quick glance at the departure board and for public transportation geeks looking for details about specific trains.
The backend has many datasources available with it's main source being IRIS-TTS - Deutsche Bahn.

<del>This integration works great side-by-side with [ha-bahnvorhersage](https://github.com/FaserF/ha-bahnvorhersage).</del>
This is a superior to [ha-deutschebahn](https://github.com/FaserF/ha-deutschebahn).

<img src="images/logo.png" alt="Logo" width="300px">

<img src="images/sensor.png" alt="Station Sensor" width="300px">

## Installation
### 1. Using HACS (recommended way)

This integration is NO official HACS Integration right now.

Open HACS then install the "db-infoscreen" integration or use the link below.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-db_infoscreen&category=integration)

If you use this method, your component will always update to the latest version.

### 2. Manual

- Download the latest zip release from [here](https://github.com/FaserF/ha-db_infoscreen/releases/latest)
- Extract the zip file
- Copy the folder "db_infoscreen" from within custom_components with all of its components to `<config>/custom_components/`

where `<config>` is your Home Assistant configuration directory.

>__NOTE__: Do not download the file by using the link above directly, the status in the "master" branch can be in development and therefore is maybe not working.

## Configuration

Go to Configuration -> Integrations and click on "add integration". Then search for "db-infoscreen".

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=db_infoscreen)

You can set up one sensor per station, except using different `via_stations` configurations.

### Configuration Variables

| Key                      | Type    | Required | Default | Description |
|--------------------------|---------|----------|---------|-------------|
| `station`               | string  | Yes      | -       | The name of the station or Trip number to be tracked. |
| `next_departures`       | int     | No       | 4       | Number of upcoming departures to display. Please note that there may be displayed less than your number, due to [storage limitations](https://github.com/FaserF/ha-db_infoscreen/issues/22). |
| `update_interval`       | int     | No       | 3       | Time interval (in minutes) to fetch updated departure data. Minimum: 1 minute. |
| `hide_low_delay`        | boolean | No       | False   | Hide departures with a delay of less than 5 minutes. |
| `drop_late_trains`      | boolean | No       | False   | Hide past departures that would still be delayed. |
| `detailed`             | boolean | No       | False   | Show additional details about departures. |
| `past_60_minutes`      | boolean | No       | False   | Show departures from the past 60 minutes. |
| `keep_route`           | boolean | No       | False   | Keep route (stopover) details (all train stations on train route). |
| `keep_endstation`      | boolean | No       | False   | Keep departure if station is also endstation. |
| `custom_api_url`       | string  | No       | -       | Use a custom API URL instead of the default one. |
| `data_source`          | string  | No       | IRIS-TTS | Choose the data source for fetching departure information. More details can be found below at Data Sources. |
| `offset`              | string  | No       | 00:00   | Time offset for departure search (HH:MM or HH:MM:SS). |
| `admode`              | string  | No       | departure preferred | Defines whether to display departure or arrival times. |
| `platforms`           | string  | No       | -       | Filter by specific platform(s) (comma-separated). |
| `via_stations`        | string  | No       | -       | Filter by stations where the train must pass through. |
| `ignored_train_types` | list    | No       | []      | List of train types to ignore (may not work for all data sources, e.g., VMT). |

#### Warnings and Limitations

- **Sensor limits:** You are limited to adding 30 sensors, if you are not using a custom_api_url. This is due to backend limitations, see [here](https://dbf.finalrewind.org/) under "API".
- **Storage Limitations:** Certain configurations (e.g., `detailed`, `keep_route`, or many `next_departures`) may quickly lead to reaching storage limitations. See [issue #22](https://github.com/FaserF/ha-db_infoscreen/issues/22) for details.
- **Data Accuracy:** The accuracy of the departure information depends on the selected `data_source`. Some sources may provide outdated or incomplete data.
- **Update Interval:** The minimum `update_interval` is 1 minute. A lower interval may cause high API usage and lead to throttling or bans. This is due to backend limitations, see [here](https://dbf.finalrewind.org/) under "API".
- **Custom API URL:** If using `custom_api_url`, ensure that the API follows the expected response format to avoid errors.


#### Data Sources
Supported are only available [Backend Sources from DBF](https://dbf.finalrewind.org/_backend). There is no way for me to support other sources than that. The mentioned sources there are all using HAFAS or EFA. If you are missing a source that uses HAFAS or EFA, you can create a feature request at [a db-infoscreen - (formerly db-fakedisplay)](https://github.com/derf/db-fakedisplay/tree/main).


- **data_source** (optional): Choose the data source for fetching departure information. The available options are:
  - The integration supports fetching departure data from various data sources, including:
    - IRIS-TTS – Deutsche Bahn (default and used by most)
    - AVV – Aachener Verkehrsverbund Nordrhein-Westfalen (avv.de)
    - BART – Bay Area Rapid Transit California (bart.gov)
    - BLS – BLS AG Kanton Bern, Kanton Luzern (bls.ch)
    - BVG – Berliner Verkehrsbetriebe Berlin, Brandenburg (bvg.de)
    - BSVG – Braunschweiger Verkehrs-GmbH
    - bwegt - Personennahverkehr in Baden-Württemberg (ehem. 3-Löwen-Takt)
    - CMTA – Capital Metro Austin Public Transport Texas (capmetro.org)
    - DING – Donau-Iller Nahverkehrsverbund
    - DSB – Rejseplanen Dänemark (rejseplanen.dk)
    - IE – Iarnród Éireann Irland, Nordirland (irishrail.ie)
    - KVV – Karlsruher Verkehrsverbund Baden-Württemberg
    - KVB – Kölner Verkehrs-Betriebe (kvb.koeln)
    - LinzAG – Linz AG
    - mobiliteit – mobilitéits zentral Luxembourg (mobiliteit.lu)
    - MVV – Münchener Verkehrs- und Tarifverbund Bayern
    - NAHSH – Nahverkehrsverbund Schleswig-Holstein Schleswig-Holstein (nah.sh)
    - NASA – Personennahverkehr in Sachsen-Anhalt Sachsen-Anhalt (nasa.de)
    - NVBW – Nahverkehrsgesellschaft Baden-Württemberg
    - NVV – Nordhessischer Verkehrsverbund Hessen (nvv.de)
    - NWL – Nahverkehr Westfalen-Lippe
    - ÖBB – Österreichische Bundesbahnen Österreich
    - PKP - Polskie Koleje Państwowe PL (polnische Staatsbahn)
    - Resrobot – Resrobot
    - RMV – Rhein-Main-Verkehrsverbund Hessen, Baden-Württemberg, Bayern, Rheinland-Pfalz (rmv.de)
    - RSAG – Rostocker Straßenbahn Mecklenburg-Vorpommern (rsag-online.de)
    - SaarVV – Saarländischer Verkehrsverbund DE-SL (saarvv.de)
    - STV – Steirischer Verkehrsverbund AT-6 (verbundlinie.at)
    - TPG – Transports publics genevois Kanton Genf (tpg.ch)
    - VAG - Freiburger Verkehrs AG
    - VBB – Verkehrsverbund Berlin-Brandenburg Berlin, Brandenburg (vbb.de)
    - VBN – Verkehrsverbund Bremen/Niedersachsen Niedersachsen, Bremen (vbn.de)
    - VGN – Verkehrsverbund Großraum Nürnberg Bayern
    - VMT – Verkehrsverbund Mittelthüringen Thüringen (vmt-thueringen.de)
    - VMV – Verkehrsgesellschaft Mecklenburg-Vorpommern Mecklenburg-Vorpommern
    - VOS – Verkehrsgemeinschaft Osnabrück Niedersachsen (vos.info)
    - VVO – Verkehrsverbund Oberelbe
    - VVS – Verkehrs- und Tarifverbund Stuttgart Baden-Württemberg
    - VRN – Verkehrsverbund Rhein-Neckar (Nordrhein-Westfalen) (EFA)
    - VRN2 – Verkehrsverbund Rhein-Neckar (Rheinland-Pfalz, Hessen, Baden-Württemberg) (HAFAS)
    - VRR – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - VRR2 – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - VRR3 – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - ZVV – Züricher Verkehrsverbund Kanton Zürich (zvv.ch)
  - Some stations can be searched via "IRIS-TTS" but need hafas=1 for data retrival, f.e. "Frankenforst Kippekausen, Bergisch Gladbach", choose `hafas=1` in the list to archive this. [GitHub issue about this](https://github.com/FaserF/ha-db_infoscreen/issues/8)


### Migrating from [ha-deutschebahn](https://github.com/FaserF/ha-deutschebahn)

Migration from `ha-deutschebahn` to `ha-db_infoscreen` is not directly possible because the two integrations use different API sources and data structures. The old `ha-deutschebahn` API supported start and destination stations directly, which the new `ha-db_infoscreen` API cannot fully replicate. However, you can still achieve a similar experience with a few workarounds:

#### Options to Achieve a "Start to Destination" Experience:

1. **Use the `platforms` Parameter**
   You can display only one direction by filtering for specific platforms. For example, show only trains from Munich to Augsburg, and then filter by specific end stations on the way.

2. **Use Two Sensors**
   To simulate a fixed start-to-destination route, create two sensors for the same station but with different `via_stations`. This will allow you to simulate the direction from the start station to the destination.

---

#### Example for Using `via_stations`

If you want to see trains departing from Munich Hbf to Augsburg Hbf, you can configure it as follows:

```yaml
sensor:
  - platform: db_infoscreen
    station: "München Hbf"
    next_departures: 4
    via_stations: "Augsburg Hbf"
    platforms: "5,6"
```

This configuration will display only the relevant departures from Munich to Augsburg, excluding the return trips.

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
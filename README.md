[![hacs_badge](https://img.shields.io/badge/HACS-CUSTOM-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# db-infoscreen Homeassistant Sensor
The `db-infoscreen` sensor will give you the departure time of the next trains for the given station, containing many more attribute informations. It aims to aggregate departure and train data from different sources and combine them in a useful (and user-friendly) manner. It is intended both for a quick glance at the departure board and for public transportation geeks looking for details about specific trains.
The backend has many datasources available with it's main source being IRIS-TTS - Deutsche Bahn.

This integration works great side-by-side with [ha-bahnvorhersage](https://github.com/FaserF/ha-bahnvorhersage).
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
| `next_departures`       | int     | No       | 4       | Number of upcoming departures to display. |
| `update_interval`       | int     | No       | 3       | Time interval (in minutes) to fetch updated departure data. Minimum: 1 minute. |
| `hide_low_delay`        | boolean | No       | False   | Hide departures with a delay of less than 5 minutes. |
| `drop_late_trains`      | boolean | No       | False   | Hide past departures that would still be delayed. |
| `detailed`             | boolean | No       | False   | Show additional details about departures. |
| `past_60_minutes`      | boolean | No       | False   | Show departures from the past 60 minutes. |
| `custom_api_url`       | string  | No       | -       | Use a custom API URL instead of the default one. |
| `data_source`          | string  | No       | IRIS-TTS | Choose the data source for fetching departure information. More details can be found below at Data Sources |
| `offset`              | string  | No       | 00:00   | Time offset for departure search (HH:MM or HH:MM:SS). |
| `admode`              | string  | No       | departure preferred | Defines whether to display departure or arrival times. |
| `platforms`           | string  | No       | -       | Filter by specific platform(s) (comma-separated). |
| `via_stations`        | string  | No       | -       | Filter by stations where the train must pass through. |
| `ignored_train_types` | list    | No       | []      | List of train types to ignore. |

Note: You are limited to adding 30 sensors, if you are not using a custom_api_url.

#### Data Sources
- **data_source** (optional): Choose the data source for fetching departure information. The available options are:
  - The integration supports fetching departure data from various data sources, including:
    - IRIS-TTS – Deutsche Bahn (default and used by most)
    - MVV – Münchener Verkehrs- und Tarifverbund Bayern
    - ÖBB – Österreichische Bundesbahnen Österreich
    - BSVG – Braunschweiger Verkehrs-GmbH
    - DING – Donau-Iller Nahverkehrsverbund
    - KVV – Karlsruher Verkehrsverbund Baden-Württemberg
    - LinzAG – Linz AG
    - NVBW – Nahverkehrsgesellschaft Baden-Württemberg
    - NWL – Nahverkehr Westfalen-Lippe
    - VGN – Verkehrsverbund Großraum Nürnberg Bayern
    - VMV – Verkehrsgesellschaft Mecklenburg-Vorpommern Mecklenburg-Vorpommern
    - VRN – Verkehrsverbund Rhein-Neckar (Nordrhein-Westfalen) (EFA)
    - VRN2 – Verkehrsverbund Rhein-Neckar (Rheinland-Pfalz, Hessen, Baden-Württemberg) (HAFAS)
    - VRR – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - VRR2 – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - VRR3 – Verkehrsverbund Rhein-Ruhr Nordrhein-Westfalen
    - VVO – Verkehrsverbund Oberelbe
    - VVS – Verkehrs- und Tarifverbund Stuttgart Baden-Württemberg
    - bwegt – bwegt Baden-Württemberg
    - AVV – Aachener Verkehrsverbund Nordrhein-Westfalen (avv.de)
    - BART – Bay Area Rapid Transit California (bart.gov)
    - BLS – BLS AG Kanton Bern, Kanton Luzern (bls.ch)
    - BVG – Berliner Verkehrsbetriebe Berlin, Brandenburg (bvg.de)
    - CMTA – Capital Metro Austin Public Transport Texas (capmetro.org)
    - DSB – Rejseplanen Dänemark (rejseplanen.dk)
    - IE – Iarnród Éireann Irland, Nordirland (irishrail.ie)
    - KVB – Kölner Verkehrs-Betriebe (kvb.koeln)
    - NAHSH – Nahverkehrsverbund Schleswig-Holstein Schleswig-Holstein (nah.sh)
    - NASA – Personennahverkehr in Sachsen-Anhalt Sachsen-Anhalt (nasa.de)
    - NVV – Nordhessischer Verkehrsverbund Hessen (nvv.de)
    - RMV – Rhein-Main-Verkehrsverbund Hessen, Baden-Württemberg, Bayern, Rheinland-Pfalz (rmv.de)
    - RSAG – Rostocker Straßenbahn Mecklenburg-Vorpommern (rsag-online.de)
    - Resrobot – Resrobot
    - STV – Steirischer Verkehrsverbund AT-6 (verbundlinie.at)
    - SaarVV – Saarländischer Verkehrsverbund DE-SL (saarvv.de)
    - TPG – Transports publics genevois Kanton Genf (tpg.ch)
    - VBB – Verkehrsverbund Berlin-Brandenburg Berlin, Brandenburg (vbb.de)
    - VBN – Verkehrsverbund Bremen/Niedersachsen Niedersachsen, Bremen (vbn.de)
    - VMT – Verkehrsverbund Mittelthüringen Thüringen (vmt-thueringen.de)
    - VOS – Verkehrsgemeinschaft Osnabrück Niedersachsen (vos.info)
    - ZVV – Züricher Verkehrsverbund Kanton Zürich (zvv.ch)
    - mobiliteit – mobilitéits zentral Luxembourg (mobiliteit.lu)
  - Some stations can be searched via "IRIS-TTS" but need hafas=1 for data retrival, f.e. "Frankenforst Kippekausen, Bergisch Gladbach", choose `hafas=1` in the list to archive this. [GitHub issue about this](https://github.com/FaserF/ha-db_infoscreen/issues/8)

### Migrating from [ha-deutschebahn](https://github.com/FaserF/ha-deutschebahn)
There is no direct way of migrating the ha-deutschebahn integration to ha-db_infoscreen due to the fact, that those are two completly different integrations with different API sources. The old ha-deutschebahn api provided a start and destination option, which is not (yet) available with this newer API backend.
To get a most similar option about this, I recommend starting playing around with the `platforms` option to only display one direction for your direction and afterwards filtering with a custom sensor to only display trains with a specific end station or using for example two sensors for the same station but choosing different `via_stations` to only display "one direction".

All other features of ha-deutschebahn are ported to this integration or will be ported soon.

[Discussion about this](https://github.com/FaserF/ha-db_infoscreen/issues/4)

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
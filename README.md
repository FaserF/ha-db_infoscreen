[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# db-infoscreen Homeassistant Sensor
The `db-infoscreen` sensor will give you the departure time of the next trains for the given station, containing many more attribute informations. It aims to aggregate departure and train data from different sources and combine them in a useful (and user-friendly) manner. It is intended both for a quick glance at the departure board and for public transportation geeks looking for details about specific trains. 

This is the superior to [ha-deutschebahn](https://github.com/FaserF/ha-deutschebahn).

<img src="images/sensor.png" alt="Station Sensor" width="300px">

## Installation
### 1. Using HACS (recommended way)

This integration NO official HACS Integration right now.

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

### Configuration Variables
- **station**: The name of the station to be tracked.
- **next_departures** (optional): The number of upcoming departures to display. Default is 4, but you can adjust it according to your preferences.
- **update_interval** (optional): The time interval (in minutes) at which the integration will fetch updated departure data. Default is 3 minutes.
- **hide_low_delay** (optional): If enabled, departures with a delay of less than 5 minutes will be hidden. Default is false.
- **detailed** (optional): If enabled, additional details about the departures will be shown. Default is false.
- **past_60_minutes** (optional): If enabled, shows departures from the past 60 minutes. Default is false.
- **custom_api_url** (optional): If you wish to use a custom API URL instead of the default one, you can specify it here. The URL should contain only the base domain (e.g., `https://example.com`).
- **data_source** (optional): Choose the data source for fetching departure information. The available options are:
  - **IRIS-TTS** (default): Uses the default DB data source.
  - **MVV**: Adds the `?efa=MVV` parameter to the URL to fetch data from the MVV system.
  - **ÖBB**: Adds the `?hafas=ÖBB` parameter to the URL to fetch data from the ÖBB system.
- **offset** (optional): Do not display departures leaving sooner than this number of seconds. You can specify the offset in "HH:MM" or "HH:MM:SS" format. Default is `00:00` (no offset).

## Accessing the data

### Automations
```yaml
automation:
```

### Custom sensor
Add a custom sensor in your configuration.yaml

```yaml
sensor:
  - platform: template
    sensors:
      next_train_departure:
        friendly_name: "Next Train Departure"
        value_template: "{{ state_attr('sensor.station_departures', 'Next departures')[0].scheduledArrival }}"
        icon_template: mdi:train
```

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
The data is coming from the [dbf.finalrewind.org](https://dbf.finalrewind.org/) website.

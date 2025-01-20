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

Go to Configuration -> Integrations and click on "add integration". Then search for "Deutsche Bahn".

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=db_infoscreen)

### Configuration Variables
- **station**: The name of the station to be tracked.
- **offset** (optional): Do not display departures leaving sooner than this number of seconds. Useful if you are a couple of minutes away from the stop. 
- **products to ignore** (optional - default is empty): Filter train types, that should be excluded
- **maximum connections** (optional - default is 2): Specify how many next connections should be fetched

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

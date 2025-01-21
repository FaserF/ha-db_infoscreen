DOMAIN = "db_infoscreen"

CONF_STATION = "station"
CONF_NEXT_DEPARTURES = "next_departures"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_NEXT_DEPARTURES = 4
DEFAULT_UPDATE_INTERVAL = 3
MIN_UPDATE_INTERVAL = 1
MAX_SENSORS = 30

CONF_HIDE_LOW_DELAY = "hidelowdelay"
CONF_DETAILED = "detailed"
CONF_PAST_60_MINUTES = "past_60_minutes"
CONF_CUSTOM_API_URL = "custom_api_url"
CONF_DATA_SOURCE = "data_source"
CONF_OFFSET = "offset"
DEFAULT_OFFSET = "00:00"
CONF_PLATFORMS = "platforms"
CONF_ADMODE = "admode"

CONF_IGNORED_PRODUCTS = "ignored_products"
CONF_IGNORED_PRODUCTS_OPTIONS = {
    "BUS": "Busverkehr (BUS)",
    "STR": "Straßenbahn (STR)",
    "S": "Stadtbahn (S-Bahn)",
    "RE": "Regional Express (RE)",
    "RB": "Regional Bahn (RB)",
    "EC": "EuroCity (EC)",
    "IC": "Intercity (IC)",
    "ICE": "Intercity Express (ICE)",
    "BRB": "Bayrische Regionalbahn"
}
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
CONF_VIA_STATIONS = "via_stations"
CONF_DIRECTION = "direction"
CONF_EXCLUDED_DIRECTIONS = "excluded_directions"
CONF_IGNORED_TRAINTYPES = "ignored_train_types"
CONF_DROP_LATE_TRAINS = "drop_late_trains"
CONF_KEEP_ROUTE = "keep_route"
CONF_KEEP_ENDSTATION = "keep_endstation"
CONF_DEDUPLICATE_DEPARTURES = "deduplicate_departures"
CONF_ENABLE_TEXT_VIEW = "enable_text_view"
CONF_EXCLUDE_CANCELLED = "exclude_cancelled"

TRAIN_TYPE_MAPPING = {
    "S": "S-Bahn",
    "N": "Regionalbahn (DB)",
    "D": "Regionalbahn",
    "F": "Intercity (Express) / Eurocity",
    "Unknown": "Unbekannter Zugtyp",
    "": "Unbekannter Zugtyp",
}

DATA_SOURCE_OPTIONS = [
    "IRIS-TTS",
    "hafas=1",
    "AVV (Aachen)",
    "AVV (Augsburg)",
    "BART",
    "BEG",
    "BLS",
    "BSVG",
    "BVG",
    "bwegt",
    "CMTA",
    "DING",
    "DSB",
    "IE",
    "KVV",
    "KVB",
    "LinzAG",
    "mobiliteit",
    "MVV",
    "NAHSH",
    "NASA",
    "NVBW",
    "NVV",
    "NWL",
    "\u00d6BB",
    "PKP",
    "Resrobot",
    "RMV",
    "Rolph",
    "RSAG",
    "RVV",
    "SaarVV",
    "STV",
    "TPG",
    "VAG",
    "VBB",
    "VBN",
    "VGN",
    "VMT",
    "VMV",
    "VOS",
    "VRN",
    "VRN2",
    "VRR",
    "VRR2",
    "VRR3",
    "VVO",
    "VVS",
    "ZVV",
]

IGNORED_TRAINTYPES_OPTIONS = {
    "S": "Stadtbahn (S-Bahn)",
    "U-Bahn": "Untergrundbahn (U-Bahn)",
    "StadtBus": "Stadtbus",
    "N": "Regional Bahn (RB), Regional Express (RE)",
    "D": "Andere Regionalbahn (z.B. BRB, Wiener Bahn)",
    "F": "EuroCity (EC), Intercity Express (ICE), Intercity (IC)",
    "Unbekannter Zugtyp": "Unbekannter Zugtyp",
}

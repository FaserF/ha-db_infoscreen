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
    "AVV – Aachener Verkehrsverbund",
    "AVV – Augsburger Verkehrs- & Tarifverbund",
    "BART – Bay Area Rapid Transit",
    "BEG – Bayerische Eisenbahngesellschaft",
    "BLS – BLS AG",
    "BSVG – Braunschweiger Verkehrs-GmbH",
    "BVG – Berliner Verkehrsbetriebe",
    "CFL – Société Nationale des Chemins de Fer Luxembourgeois",
    "CMTA – Capital Metro Austin Public Transport",
    "DING – Donau-Iller Nahverkehrsverbund",
    "DSB – Rejseplanen",
    "IE – Iarnród Éireann",
    "KVB – Kölner Verkehrs-Betriebe",
    "KVV – Karlsruher Verkehrsverbund",
    "LinzAG – Linz AG",
    "MVV – Münchener Verkehrs- und Tarifverbund",
    "NAHSH – Nahverkehrsverbund Schleswig-Holstein",
    "NASA – Personennahverkehr in Sachsen-Anhalt",
    "NVBW – Nahverkehrsgesellschaft Baden-Württemberg",
    "NVV – Nordhessischer Verkehrsverbund",
    "NWL – Nahverkehr Westfalen-Lippe",
    "PKP – Polskie Koleje Państwowe",
    "RMV – Rhein-Main-Verkehrsverbund",
    "RSAG – Rostocker Straßenbahn",
    "RVV – Regensburger Verkehrsverbund",
    "Resrobot – Resrobot",
    "Rolph – Rolph",
    "STV – Steirischer Verkehrsverbund",
    "SaarVV – Saarländischer Verkehrsverbund",
    "TPG – Transports publics genevois",
    "VAG – Freiburger Verkehrs AG",
    "VBB – Verkehrsverbund Berlin-Brandenburg",
    "VBN – Verkehrsverbund Bremen/Niedersachsen",
    "VGN – Verkehrsverbund Großraum Nürnberg",
    "VMT – Verkehrsverbund Mittelthüringen",
    "VMV – Verkehrsgesellschaft Mecklenburg-Vorpommern",
    "VOS – Verkehrsgemeinschaft Osnabrück",
    "VRN – Verkehrsverbund Rhein-Neckar",
    "VRR – Verkehrsverbund Rhein-Ruhr",
    "VRR2 – Verkehrsverbund Rhein-Ruhr",
    "VRR3 – Verkehrsverbund Rhein-Ruhr",
    "VVO – Verkehrsverbund Oberelbe",
    "VVS – Verkehrs- und Tarifverbund Stuttgart",
    "ZVV – Züricher Verkehrsverbund",
    "bwegt – bwegt",
    "mobiliteit – mobilitéits zentral",
    "ÖBB – Österreichische Bundesbahnen",
]

DATA_SOURCE_MAP = {
    "AVV – Aachener Verkehrsverbund": "hafas=AVV",
    "AVV – Augsburger Verkehrs- & Tarifverbund": "efa=AVV",
    "BART – Bay Area Rapid Transit": "hafas=BART",
    "BEG – Bayerische Eisenbahngesellschaft": "efa=BEG",
    "BLS – BLS AG": "hafas=BLS",
    "BSVG – Braunschweiger Verkehrs-GmbH": "efa=BSVG",
    "BVG – Berliner Verkehrsbetriebe": "hafas=BVG",
    "CFL – Société Nationale des Chemins de Fer Luxembourgeois": "hafas=CFL",
    "CMTA – Capital Metro Austin Public Transport": "hafas=CMTA",
    "DING – Donau-Iller Nahverkehrsverbund": "efa=DING",
    "DSB – Rejseplanen": "hafas=DSB",
    "IE – Iarnród Éireann": "hafas=IE",
    "KVB – Kölner Verkehrs-Betriebe": "hafas=KVB",
    "KVV – Karlsruher Verkehrsverbund": "efa=KVV",
    "LinzAG – Linz AG": "efa=LinzAG",
    "MVV – Münchener Verkehrs- und Tarifverbund": "efa=MVV",
    "NAHSH – Nahverkehrsverbund Schleswig-Holstein": "hafas=NAHSH",
    "NASA – Personennahverkehr in Sachsen-Anhalt": "hafas=NASA",
    "NVBW – Nahverkehrsgesellschaft Baden-Württemberg": "efa=NVBW",
    "NVV – Nordhessischer Verkehrsverbund": "hafas=NVV",
    "NWL – Nahverkehr Westfalen-Lippe": "efa=NWL",
    "PKP – Polskie Koleje Państwowe": "hafas=PKP",
    "RMV – Rhein-Main-Verkehrsverbund": "hafas=RMV",
    "RSAG – Rostocker Straßenbahn": "hafas=RSAG",
    "RVV – Regensburger Verkehrsverbund": "efa=RVV",
    "Resrobot – Resrobot": "hafas=Resrobot",
    "Rolph – Rolph": "efa=Rolph",
    "STV – Steirischer Verkehrsverbund": "hafas=STV",
    "SaarVV – Saarländischer Verkehrsverbund": "hafas=SaarVV",
    "TPG – Transports publics genevois": "hafas=TPG",
    "VAG – Freiburger Verkehrs AG": "efa=VAG",
    "VBB – Verkehrsverbund Berlin-Brandenburg": "hafas=VBB",
    "VBN – Verkehrsverbund Bremen/Niedersachsen": "hafas=VBN",
    "VGN – Verkehrsverbund Großraum Nürnberg": "efa=VGN",
    "VMT – Verkehrsverbund Mittelthüringen": "hafas=VMT",
    "VMV – Verkehrsgesellschaft Mecklenburg-Vorpommern": "efa=VMV",
    "VOS – Verkehrsgemeinschaft Osnabrück": "hafas=VOS",
    "VRN – Verkehrsverbund Rhein-Neckar": "efa=VRN",
    "VRR – Verkehrsverbund Rhein-Ruhr": "efa=VRR",
    "VRR2 – Verkehrsverbund Rhein-Ruhr": "efa=VRR2",
    "VRR3 – Verkehrsverbund Rhein-Ruhr": "efa=VRR3",
    "VVO – Verkehrsverbund Oberelbe": "efa=VVO",
    "VVS – Verkehrs- und Tarifverbund Stuttgart": "efa=VVS",
    "ZVV – Züricher Verkehrsverbund": "hafas=ZVV",
    "bwegt – bwegt": "efa=bwegt",
    "mobiliteit – mobilitéits zentral": "hafas=mobiliteit",
    "ÖBB – Österreichische Bundesbahnen": "hafas=ÖBB",
}


def normalize_data_source(value: str) -> str:
    """Normalize legacy data source values to descriptive keys."""
    if value in DATA_SOURCE_OPTIONS:
        return value

    if value == "hafas=1":
        return "hafas=1"

    # Handle patterns: exact code -> find matching key containing that code
    # e.g., "NVBW" or "efa=NVBW"
    code = value
    if "=" in value:
        code = value.split("=", 1)[1]

    for option, mapped_val in DATA_SOURCE_MAP.items():
        if code in mapped_val:
            return option

    return value


IGNORED_TRAINTYPES_OPTIONS = {
    "S": "Stadtbahn (S-Bahn)",
    "U-Bahn": "Untergrundbahn (U-Bahn)",
    "StadtBus": "Stadtbus",
    "N": "Regional Bahn (RB), Regional Express (RE)",
    "D": "Andere Regionalbahn (z.B. BRB, Wiener Bahn)",
    "F": "EuroCity (EC), Intercity Express (ICE), Intercity (IC)",
    "Unbekannter Zugtyp": "Unbekannter Zugtyp",
}

CONF_SHOW_OCCUPANCY = "show_occupancy"

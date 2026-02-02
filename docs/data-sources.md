# Data Sources 📡

`ha-db_infoscreen` supports a wide variety of public transit backends through the [db-fakedisplay](https://github.com/derf/db-fakedisplay) API.

---

## How Data Sources Work

The integration queries departure data from `dbf.finalrewind.org`. By default, it uses **IRIS-TTS** (Deutsche Bahn), which provides high-fidelity data for most German train stations.

For regional transit or international travel, you can select a different backend in the **Advanced Options** during setup or in the **Configure** menu afterward.

---

## 🇩🇪 Germany

These backends cover regional and national transit within Germany.

| Backend | Full Name |
| :--- | :--- |
| **IRIS-TTS** | Deutsche Bahn (Default / Recommended) |
| **AVV** | Aachener Verkehrsverbund |
| **AVV** | Augsburger Verkehrs- & Tarifverbund |
| **BEG** | Bayerische Eisenbahngesellschaft |
| **BSVG** | Braunschweiger Verkehrs-GmbH |
| **BVG** | Berliner Verkehrsbetriebe |
| **DING** | Donau-Iller Nahverkehrsverbund |
| **KVB** | Kölner Verkehrs-Betriebe |
| **KVV** | Karlsruher Verkehrsverbund |
| **MVV** | Münchener Verkehrs- und Tarifverbund |
| **NAHSH** | Nahverkehrsverbund Schleswig-Holstein |
| **NASA** | Personennahverkehr in Sachsen-Anhalt |
| **NVBW** | Nahverkehrsgesellschaft Baden-Württemberg |
| **NVV** | Nordhessischer Verkehrsverbund |
| **NWL** | Nahverkehr Westfalen-Lippe |
| **RMV** | Rhein-Main-Verkehrsverbund |
| **RSAG** | Rostocker Straßenbahn |
| **RVV** | Regensburger Verkehrsverbund |
| **SaarVV** | Saarländischer Verkehrsverbund |
| **VAG** | Freiburger Verkehrs AG |
| **VBB** | Verkehrsverbund Berlin-Brandenburg |
| **VBN** | Verkehrsverbund Bremen/Niedersachsen |
| **VGN** | Verkehrsverbund Großraum Nürnberg |
| **VMT** | Verkehrsverbund Mittelthüringen |
| **VMV** | Verkehrsgesellschaft Mecklenburg-Vorpommern |
| **VOS** | Verkehrsgemeinschaft Osnabrück |
| **VRN** | Verkehrsverbund Rhein-Neckar |
| **VRR** | Verkehrsverbund Rhein-Ruhr |
| **VVO** | Verkehrsverbund Oberelbe |
| **VVS** | Verkehrs- und Tarifverbund Stuttgart |
| **bwegt** | bwegt |

---

## 🌍 International

These backends cover transit systems in Austria, Switzerland, Luxembourg, Denmark, Ireland, Poland, Sweden, and the USA.

| Backend | Full Name | Country |
| :--- | :--- | :--- |
| **ÖBB** | Österreichische Bundesbahnen | 🇦🇹 Austria |
| **BLS** | BLS AG | 🇨🇭 Switzerland |
| **CFL** | Société Nationale des Chemins de Fer Luxembourgeois | 🇱🇺 Luxembourg |
| **DSB** | Rejseplanen | 🇩🇰 Denmark |
| **IE** | Iarnród Éireann | 🇮🇪 Ireland |
| **LinzAG** | Linz AG | 🇦🇹 Austria |
| **PKP** | Polskie Koleje Państwowe | 🇵🇱 Poland |
| **Resrobot** | Resrobot | 🇸🇪 Sweden |
| **Rolph** | Rolph | 🇱🇺 Luxembourg |
| **STV** | Steirischer Verkehrsverbund | 🇦🇹 Austria |
| **TPG** | Transports publics genevois | 🇨🇭 Switzerland |
| **ZVV** | Züricher Verkehrsverbund | 🇨🇭 Switzerland |
| **mobiliteit** | mobilitéits zentral | 🇱🇺 Luxembourg |
| **BART** | Bay Area Rapid Transit | 🇺🇸 USA |
| **CMTA** | Capital Metro Austin Public Transport | 🇺🇸 USA |

---

## Selecting a Data Source

1.  **During Setup**: Enable "Show Advanced Options" in the details step.
2.  **After Setup**: Go to **Settings → Devices & Services → DB Infoscreen** → **Configure** → **Advanced Options**.

!!! tip "Finding the Right Backend"
    If your local station isn't found with IRIS-TTS, try your regional network (e.g., MVV for Munich, VRN for Mannheim/Heidelberg).

---

## 🔄 Automatic Updates

This list is automatically synchronized with `dbf.finalrewind.org` via a monthly GitHub Action.

[View the update script](https://github.com/FaserF/ha-db_infoscreen/blob/main/scripts/update_backends.py){ .md-button }

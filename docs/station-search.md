# Station Search & Autocomplete 🔍

The DB Infoscreen integration features an intelligent station search system that helps you find the correct official station name from the DBF database.

---

## 🎯 How It Works

When adding a new sensor, you'll be guided through a **multi-step configuration flow**:

### Step 1: Search Station
Enter a search term for your desired station. The system will query the official DBF station database and suggest matching results.

!!! tip "Search Strategy"
    **Use broader, simpler terms** for better results:

    - ✅ **Good**: `München`, `Frankfurt`, `Berlin`

    - ❌ **Avoid**: `München Hbf`, `Frankfurt (Main) Hauptbahnhof`

    The autocomplete will present you with the exact official names (e.g., "München Hbf", "München Ost", "München Pasing") so you can select the correct one.

### Step 2: Select Station (if multiple matches)
If your search returns multiple stations, you'll see a selection list with all matching results. Simply choose the correct station from the dropdown.

**Special case**: If no match is found in the official database, you can still proceed with your manual entry. A warning icon (⚠️) will indicate that the station name couldn't be verified.

### Step 3: Configure Details
Once the station is selected, you'll configure all sensor options (update interval, filters, platforms, etc.).

---

## 🔧 Technical Details

### Station Database
- **Source**: [DBF Autocomplete API](https://dbf.finalrewind.org/dyn/v110/autocomplete.js)
- **Update Frequency**: The station list is cached locally for 24 hours to reduce API load
- **Coverage**: Includes all stations supported by DBF (DB, ÖBB, SBB, regional transport associations)

### Matching Algorithm

The search uses a **4-tier priority matching system**:

1. **Exact Match** (case-insensitive)
   - Query: `Hamburg Hbf` → Result: `["Hamburg Hbf"]`

2. **Starts With** (case-insensitive)

   - Query: `München` → Results: `["München Hbf", "München Ost", "München Pasing", ...]`
   - Limited to 10 results to avoid overwhelming the UI

3. **Contains** (case-insensitive)

   - Query: `Flughafen` → Results: `["München Flughafen Terminal", "Frankfurt Flughafen", ...]`
   - Also limited to 10 results

4. **Fuzzy Match** (using Python's `difflib`)

   - Query: `Muenchen` → Results: `["München Hbf", "München Ost", ...]`
   - Cutoff: 0.6 similarity score
   - Catches typos and alternative spellings

### Manual Override

If you enter a station that isn't in the official IRIS list (e.g., a very new station or a custom identifier), the integration will:

-   Show a warning: `⚠️ Station not found in the official IRIS list!`

-   Allow you to proceed with your manual entry

-   Attempt to fetch data from the API using your custom identifier

This is useful for:

-   **DS100 codes** (e.g., `FF` for Frankfurt Hbf)
-   **EVA numbers** (numeric station IDs)
-   **Trip numbers** (for tracking specific train runs)

---

## 💡 Best Practices

### For City Stations
Start with the city name only:

    München → Select from: München Hbf, München Ost, München Pasing, etc.

### For Smaller Stations
Use the full station name or a unique part:

    Erlangen → Exact match: Erlangen

### For Airports
Use the keyword "Flughafen":

    Flughafen → Select from: München Flughafen Terminal, Frankfurt Flughafen, etc.

### For Ambiguous Names
If you know the region, include it:

    Neustadt → Many results
    Neustadt Weinstraße → Specific match

---

## 🐛 Troubleshooting

### "No stations found"
- **Cause**: Your search term doesn't match any station in the database
- **Solution**: Try a broader term or check the [DS100 List](https://ds100.frankfurtium.de/dumps/orte_de.html) for the official name

### "Failed to connect to DBF"
- **Cause**: The DBF API is temporarily unavailable
- **Solution**: Wait a moment and try again. The integration will use cached station data if available.

### "Station not found in official IRIS list"
- **Cause**: You entered a custom identifier (DS100, EVA, or trip number)
- **Solution**: This is expected. Proceed with your entry if you're confident it's correct. The integration will attempt to fetch data using your identifier.

### Station ID not working after update
- **Cause**: You're using a station ID (like `901795`) with a regional HAFAS backend
- **Solution**: See the HAFAS section below for the correct data source selection

---

## 🚌 Using HAFAS Station IDs (Regional Networks)

!!! important "Station IDs vs. Station Names"
    The autocomplete database only contains **official Deutsche Bahn station names**. If you're tracking a **regional bus/train stop** that's not in the DB network, you need to use a **HAFAS station ID** with the appropriate backend.

### Finding Your HAFAS Station ID

1. Visit [dbf.finalrewind.org](https://dbf.finalrewind.org)
2. Search for your station and select it
3. Note the **numeric ID** in the URL (e.g., `901795` from `https://dbf.finalrewind.org/901795?hafas=VBN`)
4. Also note the **HAFAS parameter** (e.g., `VBN`)

### Configuration Steps

1. **Enter the station ID** in the search field (e.g., `901795`)
2. When it shows "Station not found", select **Manual Entry**
3. In the manual configuration, select the correct **Data Source** matching your HAFAS backend:

-   `VBN` for Verkehrsverbund Bremen/Niedersachsen

-   `VRN` for Verkehrsverbund Rhein-Neckar

-   etc. (see [Data Sources](data-sources.md) for full list)

!!! example "Example: Bremen VBN Station"
    - **Station ID**: `901795`
    - **Data Source**: `VBN`
    - **URL Preview**: `https://dbf.finalrewind.org/901795?hafas=VBN`

### Common HAFAS Backends

| Code | Network | Region |
| :--- | :--- | :--- |
| `VBN` | Verkehrsverbund Bremen/Niedersachsen | Bremen, Lower Saxony |

| `VRN` | Verkehrsverbund Rhein-Neckar | Rhine-Neckar region |

| `AVV` | Aachener Verkehrsverbund | Aachen area |

| `VMT` | Verkehrsverbund Mittelthüringen | Central Thuringia |

| `NASA` | Nahverkehr Sachsen-Anhalt | Saxony-Anhalt |

For the complete list, see [Data Sources](data-sources.md).

---

## 🔗 Related Documentation
- [Entities Reference](entities.md)
- [Configuration Reference](configuration.md)
- [Installation Guide](installation.md)
- [Troubleshooting](troubleshooting.md)

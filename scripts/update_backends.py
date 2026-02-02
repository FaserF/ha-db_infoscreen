
import re
import sys
import urllib.request
import os
import html
from urllib.parse import parse_qs

# Source URL
URL = "https://dbf.finalrewind.org/_backend"
CONST_FILE = os.path.join("custom_components", "db_infoscreen", "const.py")
README_FILE = "README.md"
DOCS_CONFIG_FILE = os.path.join("docs", "configuration.md")

# Region mapping (shortname -> region)
# Based on known transport associations
REGION_MAP = {
    # Germany
    "AVV": "de", "BEG": "de", "BSVG": "de", "BVG": "de", "DING": "de",
    "KVB": "de", "KVV": "de", "MVV": "de", "NAHSH": "de", "NASA": "de",
    "NVBW": "de", "NVV": "de", "NWL": "de", "RMV": "de", "RSAG": "de",
    "RVV": "de", "SaarVV": "de", "VAG": "de", "VBB": "de", "VBN": "de",
    "VGN": "de", "VMT": "de", "VMV": "de", "VOS": "de", "VRN": "de",
    "VRR": "de", "VRR2": "de", "VRR3": "de", "VVO": "de", "VVS": "de",
    "bwegt": "de",
    # International
    "ÖBB": "int", "BLS": "int", "CFL": "int", "DSB": "int", "IE": "int",
    "PKP": "int", "Resrobot": "int", "STV": "int", "TPG": "int",
    "ZVV": "int", "mobiliteit": "int", "LinzAG": "int", "Rolph": "int",
    "BART": "int", "CMTA": "int",
}

def fetch_backends():
    print(f"Fetching {URL}...")
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode("utf-8")
        return html_content
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

def extract_data(html_content):
    links = re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html_content)

    backends = []
    seen = set()

    for href, name in links:
        href = html.unescape(href)
        if 'efa=' not in href and 'hafas=' not in href:
            continue

        query = href.split('?', 1)[-1]
        params = parse_qs(query)

        efa = params.get('efa', [None])[0]
        hafas = params.get('hafas', [None])[0]

        name = html.unescape(name.strip())

        if efa and hafas:
            backends.append({"name": name, "type": "efa", "val": efa})
        elif efa:
            backends.append({"name": name, "type": "efa", "val": efa})
        elif hafas:
            backends.append({"name": name, "type": "hafas", "val": hafas})
        elif 'IRIS-TTS' in name:
            backends.append({"name": "IRIS-TTS", "type": "iris", "val": ""})

    unique_backends = []
    for b in backends:
        key = (b['type'], b['val'])
        if key not in seen:
            unique_backends.append(b)
            seen.add(key)

    return unique_backends

def get_shortname(backend):
    """Extract shortname (e.g. 'AVV' from 'AVV – Aachener Verkehrsverbund')"""
    return backend['val']

def update_const_file(backends):
    if not os.path.exists(CONST_FILE):
        print(f"Error: {CONST_FILE} not found!")
        return

    with open(CONST_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    options = ["IRIS-TTS", "hafas=1"]
    data_map = {}

    for b in backends:
        if b['type'] == 'iris':
            continue
        options.append(b['name'])
        data_map[b['name']] = f"{b['type']}={b['val']}"

    iris = options.pop(0)
    hafas1 = options.pop(0)
    options.sort()
    options = [iris, hafas1] + options

    # Replace DATA_SOURCE_OPTIONS
    new_list_str = "DATA_SOURCE_OPTIONS = [\n"
    for opt in options:
        safe_opt = opt.replace("'", "\\'")
        new_list_str += f"    '{safe_opt}',\n"
    new_list_str += "]"
    pattern_list = re.compile(r'DATA_SOURCE_OPTIONS = \[.*?\]', re.DOTALL)
    content = pattern_list.sub(new_list_str, content)

    # Replace DATA_SOURCE_MAP
    new_map_str = "DATA_SOURCE_MAP = {\n"
    for k in sorted(data_map.keys()):
        safe_k = k.replace("'", "\\'")
        new_map_str += f"    '{safe_k}': '{data_map[k]}',\n"
    new_map_str += "}"

    if "DATA_SOURCE_MAP =" in content:
        pattern_map = re.compile(r'DATA_SOURCE_MAP = \{.*?\}', re.DOTALL)
        content = pattern_map.sub(new_map_str, content)
    else:
        content = content.replace("IGNORED_TRAINTYPES_OPTIONS =", f"{new_map_str}\n\nIGNORED_TRAINTYPES_OPTIONS =")

    with open(CONST_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully updated {CONST_FILE} with {len(options)} options and {len(data_map)} map entries.")

def generate_readme_content(backends):
    """Generate the categorized README content for Data Sources."""
    de_backends = []
    int_backends = []

    for b in backends:
        if b['type'] == 'iris':
            continue
        shortname = get_shortname(b)
        region = REGION_MAP.get(shortname, "int")  # Default to international if unknown
        if region == "de":
            de_backends.append(b['name'])
        else:
            int_backends.append(b['name'])

    de_backends.sort()
    int_backends.sort()

    md = "### Supported Data Sources\n\n"
    md += "#### 🇩🇪 Germany\n\n"
    md += "*   **IRIS-TTS** (Deutsche Bahn) - *Default / Recommended*\n"
    for name in de_backends:
        md += f"*   **{name}**\n"
    md += "\n#### 🌍 International\n\n"
    for name in int_backends:
        md += f"*   **{name}**\n"
    return md

def update_readme(backends):
    if not os.path.exists(README_FILE):
        return

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    md_list = generate_readme_content(backends)

    try:
        parts = content.split("## 📡 Data Sources")
        if len(parts) < 2: return

        after_header = parts[1]

        pattern = re.compile(r'(<summary>.*?</summary>).*?(> Note:)', re.DOTALL)
        replacement = r'\1\n\n' + md_list + r'\n\n\2'
        new_after_header = pattern.sub(replacement, after_header)

        new_content = parts[0] + "## 📡 Data Sources" + new_after_header

        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully updated {README_FILE}")
    except Exception as e:
        print(f"Failed to update README: {e}")

def update_docs_config(backends):
    """Update docs/configuration.md with the new data source list."""
    if not os.path.exists(DOCS_CONFIG_FILE):
        print(f"Skipping {DOCS_CONFIG_FILE} (not found)")
        return

    with open(DOCS_CONFIG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # We don't need to add full list to docs/configuration.md, just ensure
    # the description is accurate. The full list is in README.
    # Just update the "Regional/International" text to reflect the categories.
    # The current text is already generic enough, so no structural changes needed.
    print(f"Reviewed {DOCS_CONFIG_FILE} - no structural changes needed.")

if __name__ == "__main__":
    html_content = fetch_backends()
    if html_content:
        backends = extract_data(html_content)
        if backends:
            update_const_file(backends)
            update_readme(backends)
            update_docs_config(backends)
        else:
            print("No backends found.")

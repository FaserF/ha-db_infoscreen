import urllib.request
import json
import ssl

# Bypass SSL verification for simplicity in debug script
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

stations = ["Starnberg Nord", "Zorneding"]

for station in stations:
    station_encoded = urllib.parse.quote(station)
    url = f"https://dbf.finalrewind.org/{station_encoded}.json"
    print(f"Fetching data for {station} from {url}...")
    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            data = json.loads(response.read().decode())

            departures = data.get("departures", [])
            print(f"Total departures found: {len(departures)}")

            if departures:
                print("First departure sample keys:")
                print(list(departures[0].keys()))

                # Check for keys used in filtering
                dep = departures[0]
                print(f"Direction: {dep.get('direction')}")
                print(f"Train/Line: {dep.get('train')} / {dep.get('line')}")
                print(
                    f"Scheduled Time: {dep.get('scheduledDeparture') or dep.get('scheduledTime') or dep.get('sched_dep')}"
                )
                print(f"Route: {dep.get('route')}")
                print(f"Via: {dep.get('via')}")
            else:
                print("No departures returned by API.")

    except Exception as e:
        print(f"Error fetching data: {e}")
    print("-" * 40)

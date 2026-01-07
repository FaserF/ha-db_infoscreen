import argparse
import datetime
import json
import os
import re

VERSION_FILE = 'VERSION'
MANIFEST_FILE = 'custom_components/db_infoscreen/manifest.json'

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def write_version(version):
    with open(VERSION_FILE, 'w') as f:
        f.write(version)

    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, 'r') as f:
            data = json.load(f)
        data['version'] = version
        with open(MANIFEST_FILE, 'w') as f:
            json.dump(data, f, indent=2)

def calculate_version(release_type):
    current_version = get_current_version()
    now = datetime.datetime.now()
    year = now.year
    month = now.month

    # Parse current version
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(.*)", current_version)
    if match:
        curr_year, curr_month, curr_patch, suffix = match.groups()
        curr_year, curr_month, curr_patch = int(curr_year), int(curr_month), int(curr_patch)
    else:
        curr_year, curr_month, curr_patch = 0, 0, 0

    # Logic: Reset patch if Year or Month changes
    if year != curr_year or month != curr_month:
        patch = 1
    else:
        patch = curr_patch + 1

    base_version = f"{year}.{month}.{patch}"

    if release_type == 'stable':
        return base_version
    elif release_type == 'beta':
        return f"{base_version}-beta"
    elif release_type == 'nightly':
        timestamp = now.strftime("%Y%m%d.%H%M")
        return f"{base_version}-nightly.{timestamp}"
    elif release_type == 'dev':
        return f"{base_version}-dev"
    else:
        raise ValueError(f"Unknown release type: {release_type}")

def main():
    parser = argparse.ArgumentParser(description='Manage project version.')
    parser.add_argument('action', choices=['get', 'bump'], help='Action to perform')
    parser.add_argument('--type', choices=['stable', 'beta', 'nightly', 'dev'], help='Release type for bump')

    args = parser.parse_args()

    if args.action == 'get':
        print(get_current_version())
    elif args.action == 'bump':
        if not args.type:
            print("Error: --type is required for bump action")
            exit(1)
        new_version = calculate_version(args.type)
        write_version(new_version)
        print(new_version)

if __name__ == '__main__':
    main()

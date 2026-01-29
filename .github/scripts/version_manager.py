import argparse
import datetime
import json
import os
import re

VERSION_FILE = "VERSION"
MANIFEST_FILE = "custom_components/db_infoscreen/manifest.json"


def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.0.0"


def write_version(version):
    with open(VERSION_FILE, "w") as f:
        f.write(version)

    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r") as f:
            data = json.load(f)
        data["version"] = version
        with open(MANIFEST_FILE, "w") as f:
            json.dump(data, f, indent=2)


def calculate_version(release_type):
    current_version = get_current_version()
    now = datetime.datetime.now()
    year = now.year
    month = now.month

    # Parse CalVer: YEAR.MONTH.PATCH and suffix
    # Supports formats like: 2026.1.1, 2026.1.1b1, 2026.1.1-dev1
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(b)(\d+)|(-dev)(\d+))?$", current_version)

    if match:
        curr_year, curr_month, curr_patch, b_prefix, b_num, dev_prefix, dev_num = match.groups()
        curr_year, curr_month, curr_patch = int(curr_year), int(curr_month), int(curr_patch)

        if b_prefix:
            suffix_type = "b"
            suffix_num = int(b_num)
        elif dev_prefix:
            suffix_type = "-dev"
            suffix_num = int(dev_num)
        else:
            suffix_type = None
            suffix_num = 0
    else:
        # Fallback for invalid formats
        curr_year, curr_month, curr_patch = 0, 0, 0
        suffix_type = None
        suffix_num = 0

    # Logic: Reset patch if Year or Month changes
    if year != curr_year or month != curr_month:
        patch = 1
    else:
        patch = curr_patch

    if release_type == "stable":
        # If we have a suffix, "promoting" means removing the suffix from the current patch
        if suffix_type is not None:
            return f"{year}.{month}.{patch}"
        # Straight increment
        return f"{year}.{month}.{patch + 1}"

    elif release_type == "beta":
        # Already in beta? Increment beta number
        if suffix_type == "b" and year == curr_year and month == curr_month:
            return f"{year}.{month}.{patch}b{suffix_num + 1}"

        # New beta? Increment patch (if stable) and start at b0
        if suffix_type is None:
             patch += 1
        return f"{year}.{month}.{patch}b0"

    elif release_type == "nightly" or release_type == "dev":
        # Already in dev? Increment dev number
        if suffix_type == "-dev" and year == curr_year and month == curr_month:
            return f"{year}.{month}.{patch}-dev{suffix_num + 1}"

        # New dev? Increment patch (if stable) and start at dev0
        if suffix_type is None:
             patch += 1
        return f"{year}.{month}.{patch}-dev0"

    else:
        raise ValueError(f"Unknown release type: {release_type}")


def main():
    parser = argparse.ArgumentParser(description="Manage project version.")
    parser.add_argument("action", choices=["get", "bump"], help="Action to perform")
    parser.add_argument(
        "--type",
        choices=["stable", "beta", "nightly", "dev"],
        help="Release type for bump",
    )

    args = parser.parse_args()

    if args.action == "get":
        print(get_current_version())
    elif args.action == "bump":
        if not args.type:
            print("Error: --type is required for bump action")
            exit(1)
        new_version = calculate_version(args.type)
        write_version(new_version)
        print(new_version)


if __name__ == "__main__":
    main()

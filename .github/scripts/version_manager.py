import argparse
import datetime
import json
import os
import re
import subprocess

VERSION_FILE = "VERSION"
MANIFEST_FILE = "custom_components/db_infoscreen/manifest.json"


def get_current_version():
    """Get the current version from git tags (preferred) or manifest.json."""
    # 1. Try Git Tags (Strict CalVer)
    try:
        # Get all tags
        tags = (
            subprocess.check_output(["git", "tag"], stderr=subprocess.DEVNULL)
            .decode()
            .splitlines()
        )

        valid_tags = []
        for tag in tags:
            tag = tag.strip()
            match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(b)(\d+)|(-dev)(\d+))?$", tag)
            if match:
                y, m, p, b_p, b_n, d_p, d_n = match.groups()
                priority = 0
                s_num = 0
                if b_p:
                    priority = 1
                    s_num = int(b_n)
                elif d_p:
                    priority = 0
                    s_num = int(d_n)
                else:
                    priority = 2

                valid_tags.append({
                    "tag": tag,
                    "key": (int(y), int(m), int(p), priority, s_num)
                })

        if valid_tags:
            # Sort by key descending
            valid_tags.sort(key=lambda x: x["key"], reverse=True)
            return valid_tags[0]["tag"]

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 2. Try manifest.json
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            v = data.get("version", "0.0.0")
            if v != "0.0.0":
                return v

    return "2024.1.0"  # Safe baseline


def write_version(version):
    """Write version to VERSION file and manifest.json."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version)

    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["version"] = version
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def calculate_version(release_type, now=None):
    current_version = get_current_version()
    if now is None:
        now = datetime.datetime.now()
    year = now.year
    month = now.month

    # Parse CalVer: YEAR.MONTH.PATCH and suffix
    # Supports formats like: 2026.1.1, 2026.1.1b1, 2026.1.1-dev1
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(b)(\d+)|(-dev)(\d+))?$", current_version)

    if match:
        curr_year, curr_month, curr_patch, b_prefix, b_num, dev_prefix, dev_num = (
            match.groups()
        )
        curr_year, curr_month, curr_patch = (
            int(curr_year),
            int(curr_month),
            int(curr_patch),
        )

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
    is_new_cycle = year != curr_year or month != curr_month
    if is_new_cycle:
        patch = 0
    else:
        patch = curr_patch

    if release_type == "stable":
        # If we have a suffix (beta/dev), stable means "cutting the release" of THIS patch
        if suffix_type is not None:
            return f"{year}.{month}.{patch}"

        # If it's a new cycle, we start at .0
        if is_new_cycle:
            return f"{year}.{month}.0"

        # Increment patch
        return f"{year}.{month}.{patch + 1}"

    elif release_type == "beta":
        # If Year/Month changes, we start at .0b0
        if is_new_cycle:
            return f"{year}.{month}.0b0"

        # Already in beta? Increment beta number
        if suffix_type == "b":
            return f"{year}.{month}.{patch}b{suffix_num + 1}"

        # Coming from stable or dev?
        # We want to increment patch if coming from stable of the same cycle
        # If it was 2026.2.0 (stable), next beta is 2026.2.1b0
        if suffix_type is None:
            return f"{year}.{month}.{patch + 1}b0"

        # Coming from dev? Use current patch but change suffix
        return f"{year}.{month}.{patch}b0"

    elif release_type == "dev" or release_type == "nightly":
        # If Year/Month changes, we start at .0-dev0
        if is_new_cycle:
            return f"{year}.{month}.0-dev0"

        # Already in dev? Increment dev number
        if suffix_type == "-dev":
            return f"{year}.{month}.{patch}-dev{suffix_num + 1}"

        # New dev? Increment patch if coming from stable
        if suffix_type is None:
            return f"{year}.{month}.{patch + 1}-dev0"

        # Coming from beta? Just change suffix
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

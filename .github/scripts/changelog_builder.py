import subprocess
import re
import argparse


def get_commits(from_tag=None):
    """Get commits since from_tag, or all commits if from_tag is None."""
    if from_tag:
        cmd = ["git", "log", f"{from_tag}..HEAD", "--pretty=format:%H|%h|%s"]
    else:
        cmd = ["git", "log", "--pretty=format:%H|%h|%s"]

    try:
        output = subprocess.check_output(cmd, text=True).strip()
        if not output:
            return []
        return output.split("\n")
    except Exception as e:
        print(f"Error getting commits: {e}")
        return []


def build_changelog(commits, repo_url):
    """Categorize commits and build a markdown changelog."""
    cats = {
        "✨ Features": [],
        "🐛 Bug Fixes": [],
        "📦 Dependencies": [],
        "🔧 Maintenance & CI": [],
        "📝 Documentation": [],
        "🧪 Tests": [],
        "🚀 Other": [],
    }

    for line in commits:
        if not line or "|" not in line:
            continue
        full_hash, short_hash, subject = line.split("|", 2)
        subject_lower = subject.lower()

        # Skip release and merge commits
        if any(
            x in subject_lower
            for x in [
                "chore: release",
                "chore: bump",
                "merge ",
                "[skip ci]",
                "chore(release)",
                "chore(dev)",
            ]
        ):
            continue

        # Linkify PR numbers
        subject = re.sub(r"\(#(\d+)\)", rf"([#\1]({repo_url}/pull/\1))", subject)
        entry = f"- {subject} ([{short_hash}]({repo_url}/commit/{full_hash}))"

        if re.match(r"^(feat|add|new|✨)", subject_lower):
            cats["✨ Features"].append(entry)
        elif re.match(r"^(fix|bug|patch|fixed|fixes|🐛)", subject_lower):
            cats["🐛 Bug Fixes"].append(entry)
        elif re.match(r"^(deps|dep|update|bump|renovate|📦|⬆️)", subject_lower):
            cats["📦 Dependencies"].append(entry)
        elif re.match(r"^(chore|ci|workflow|config|ruff|🔧)", subject_lower):
            cats["🔧 Maintenance & CI"].append(entry)
        elif re.match(r"^(docs|documentation|📝)", subject_lower):
            cats["📝 Documentation"].append(entry)
        elif re.match(r"^(test|pytest|🧪)", subject_lower):
            cats["🧪 Tests"].append(entry)
        else:
            cats["🚀 Other"].append(entry)

    changelog = "## Changelog\n\n"
    has_content = False

    for title in [
        "✨ Features",
        "🐛 Bug Fixes",
        "📦 Dependencies",
        "🔧 Maintenance & CI",
        "📝 Documentation",
        "🧪 Tests",
        "🚀 Other",
    ]:
        items = cats[title]
        if items:
            changelog += f"### {title}\n"
            for item in items:
                changelog += f"{item}\n"
            changelog += "\n"
            has_content = True

    if not has_content:
        changelog += "No significant changes in this release."

    return changelog


def main():
    parser = argparse.ArgumentParser(description="Build a changelog from git commits.")
    parser.add_argument("--from-tag", help="Tag to start from")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--output", default="CHANGELOG_BODY.md", help="Output file")

    args = parser.parse_args()

    commits = get_commits(args.from_tag)
    changelog = build_changelog(commits, args.repo_url)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(changelog)
    print(f"Changelog written to {args.output}")


if __name__ == "__main__":
    main()

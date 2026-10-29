"""Tests to verify documentation link integrity."""

import os
import re
import pytest

DOCS_DIR = "docs"


def get_all_markdown_files():
    """Get all markdown files in the docs directory."""
    md_files = []
    if os.path.exists(DOCS_DIR):
        for root, _, files in os.walk(DOCS_DIR):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
    return md_files


class LinkValidator:
    def __init__(self):
        self.anchors = {}  # {file_rel_path: set(anchors)}
        self.files = get_all_markdown_files()

    def slugify(self, text):
        """Simple slugify matching MkDocs behavior."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\- ]", "", text)
        return text.replace(" ", "-")

    def extract_anchors(self):
        """Extract all possible anchor IDs from markdown files."""
        for file_path in self.files:
            rel_path = os.path.relpath(file_path, DOCS_DIR).replace("\\", "/")
            self.anchors[rel_path] = set()

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. Explicit anchors {: #id }
            explicit = re.findall(r"\{:\s*#([\w\-]+)\s*\}", content)
            for a in explicit:
                self.anchors[rel_path].add(a)

            # 2. Header slugs (if no explicit anchor on that line)
            for line in content.splitlines():
                if line.startswith("#"):
                    # Strip the # and explicit anchor part
                    clean_line = (
                        re.sub(r"\{:\s*#[\w\-]+\s*\}", "", line).strip("#").strip()
                    )
                    if clean_line:
                        slug = self.slugify(clean_line)
                        self.anchors[rel_path].add(slug)

    def validate_links(self):
        """Check all links in all files."""
        errors = []
        for file_path in self.files:
            current_file = os.path.relpath(file_path, DOCS_DIR).replace("\\", "/")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find markdown links: [text](link)
            # Only match relative links (no http://)
            links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", content)

            for link in links:
                if link.startswith(("http", "mailto:", "tel:")):
                    continue

                # Split path and anchor
                parts = link.split("#")
                target_file = parts[0] if parts[0] else current_file
                target_anchor = parts[1] if len(parts) > 1 else None

                # Check if target file exists
                if target_file and target_file != ".":
                    full_target_path = os.path.normpath(
                        os.path.join(DOCS_DIR, target_file)
                    )
                    if not os.path.exists(full_target_path):
                        # Try adding .md if missing
                        if not full_target_path.endswith(".md"):
                            full_target_path += ".md"

                        if not os.path.exists(full_target_path):
                            errors.append(f"Broken file link in {current_file}: {link}")
                            continue

                # Check anchor
                if target_anchor:
                    # Normalize target_file for lookup
                    lookup_file = os.path.relpath(
                        os.path.normpath(os.path.join(DOCS_DIR, target_file)), DOCS_DIR
                    ).replace("\\", "/")
                    if not lookup_file.endswith(".md"):
                        lookup_file += ".md"

                    if lookup_file not in self.anchors:
                        # Might be a directory link or something else, but we focus on .md files
                        continue

                    if target_anchor not in self.anchors[lookup_file]:
                        errors.append(
                            f"Broken anchor link in {current_file}: {link} (Anchor #{target_anchor} not found in {lookup_file})"
                        )

        return errors


def test_documentation_links():
    """Main test entry point for link validation."""
    validator = LinkValidator()
    validator.extract_anchors()
    errors = validator.validate_links()

    if errors:
        pytest.fail("\n".join(errors))

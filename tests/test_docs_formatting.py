"""Tests to ensure documentation formatting remains clean."""
import os
import pytest

DOCS_DIR = "docs"

def get_all_markdown_files():
    """Get all markdown files in the project."""
    md_files = []
    if os.path.exists(DOCS_DIR):
        for root, _, files in os.walk(DOCS_DIR):
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))
    return md_files

@pytest.mark.parametrize("file_path", get_all_markdown_files())
def test_markdown_paragraph_spacing(file_path):
    """Verify that markdown files have proper spacing between elements."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    for i in range(1, len(lines)):
        line_raw = lines[i]
        line = line_raw.strip()
        prev_line = lines[i-1].strip()

        # Rule: Top-level headers or bullets following a text line must have a blank line
        if (line_raw.startswith(("- ", "* ", "1. ", "### ", "## ", "# "))) and prev_line:
             if not prev_line.startswith(("- ", "* ", "1. ", "#", ">", "|", "!", "<", "---", "```", "{%", "%}")):
                assert False, f"Missing blank line before top-level element in {file_path} at line {i+1}"

def test_specific_user_reported_case():
    """Verify specific formatting fix in limitations.md."""
    limitations_path = os.path.join(DOCS_DIR, "limitations.md")
    if not os.path.exists(limitations_path):
        pytest.skip("limitations.md not found")

    with open(limitations_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "support a maximum of **30 sensors** per Home Assistant instance.\n\n-   **Why?**" in content

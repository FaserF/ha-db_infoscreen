"""Test the translation files."""

import json
import os
import pytest
from custom_components.db_infoscreen import DOMAIN


@pytest.fixture
def translations_path():
    """Return the path to translations."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        DOMAIN,
        "translations",
    )


@pytest.fixture
def strings_path():
    """Return the path to strings.json."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        DOMAIN,
        "strings.json",
    )


def flatten_json(y):
    """Flatten a nested json dict."""
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + ".")
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def test_translations_consistency(translations_path, strings_path):
    """Test that all strings in strings.json are present in translations."""
    with open(strings_path, "r", encoding="utf-8") as f:
        strings = json.load(f)

    flat_strings = flatten_json(strings)

    # Check all translation files
    for filename in os.listdir(translations_path):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(translations_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

        flat_trans = flatten_json(translations)
        missing_keys = []
        for key in flat_strings:
            if key not in flat_trans:
                missing_keys.append(key)

        assert not missing_keys, f"Missing keys in {filename}: {missing_keys}"

"""Test the translation files."""

import re
import json
import os
import pytest

DOMAIN = "db_infoscreen"


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


@pytest.fixture
def en_path(translations_path):
    """Return the path to en.json."""
    return os.path.join(translations_path, "en.json")


@pytest.fixture
def de_path(translations_path):
    """Return the path to de.json."""
    return os.path.join(translations_path, "de.json")


@pytest.fixture
def config_flow_path():
    """Return the path to config_flow.py."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        DOMAIN,
        "config_flow.py",
    )


@pytest.fixture
def sensor_files():
    """Return the paths to sensor files."""
    base = os.path.join(os.path.dirname(__file__), "..", "custom_components", DOMAIN)
    return [
        os.path.join(base, "sensor.py"),
        os.path.join(base, "binary_sensor.py"),
        os.path.join(base, "calendar.py"),
    ]


def flatten_json(y):
    """Flatten a nested json dict, handling lists as well."""
    out = {}

    def flatten(x, name=""):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + ".")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, name + str(i) + ".")
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
    for filename in ["en.json", "de.json"]:
        file_path = os.path.join(translations_path, filename)
        assert os.path.exists(file_path), f"Translation file {filename} missing"

        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

        flat_trans = flatten_json(translations)
        missing_keys = []
        mismatched_placeholders = []
        for key in flat_strings:
            if key not in flat_trans:
                missing_keys.append(key)
                continue

            # Check placeholders
            val_strings = str(flat_strings[key])
            val_trans = str(flat_trans[key])

            vars_strings = set(re.findall(r"\{(\w+)\}", val_strings))
            vars_trans = set(re.findall(r"\{(\w+)\}", val_trans))

            if vars_strings != vars_trans:
                mismatched_placeholders.append(
                    f"{key}: Expected {vars_strings}, got {vars_trans}"
                )

        assert not missing_keys, f"Missing keys in {filename}: {missing_keys}"
        assert (
            not mismatched_placeholders
        ), f"Placeholder mismatch in {filename}: {mismatched_placeholders}"


def test_config_flow_keys_in_strings(config_flow_path, strings_path):
    """Test that all keys used in config_flow.py are in strings.json."""
    with open(config_flow_path, "r", encoding="utf-8") as f:
        content = f.read()

    with open(strings_path, "r", encoding="utf-8") as f:
        strings = json.load(f)

    flat_strings = flatten_json(strings)

    # Find errors
    # errors["base"] = "max_sensors_reached"
    error_keys = re.findall(r'errors\["[^"]+"\]\s*=\s*"([^"]+)"', content)
    # also check dict literals in async_show_form
    error_keys.extend(re.findall(r'errors\s*=\s*\{"[^"]+"\s*:\s*"([^"]+)"\}', content))

    for key in set(error_keys):
        full_key = f"config.error.{key}"
        assert (
            full_key in flat_strings
        ), f"Error key '{key}' from config_flow.py missing in strings.json"

    # Find abort reasons
    # return self.async_abort(reason="already_configured")
    abort_reasons = re.findall(r'self\.async_abort\(reason="([^"]+)"\)', content)
    for reason in set(abort_reasons):
        full_key = f"config.abort.{reason}"
        assert (
            full_key in flat_strings
        ), f"Abort reason '{reason}' from config_flow.py missing in strings.json"

    # Find step IDs
    # step_id="user"
    step_ids = re.findall(r'step_id="([^"]+)"', content)
    for step in set(step_ids):
        # Steps can be in config or options
        # We check if it exists in either
        found = False
        if f"config.step.{step}.title" in flat_strings:
            found = True
        if f"options.step.{step}.title" in flat_strings:
            found = True

        # Skip internal steps if any (none found currently)
        if step in ["init"] and f"options.step.{step}.title" in flat_strings:
            found = True

        assert (
            found
        ), f"Step ID '{step}' from config_flow.py missing title in strings.json"


def test_sensor_translation_keys(sensor_files, strings_path):
    """Test that all translation_keys used in sensors are in strings.json."""
    with open(strings_path, "r", encoding="utf-8") as f:
        strings = json.load(f)

    flat_strings = flatten_json(strings)

    for file_path in sensor_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # _attr_translation_key = "leave_now"
        keys = re.findall(r'_attr_translation_key\s*=\s*"([^"]+)"', content)
        for key in set(keys):
            # Check if it exists in entity section
            # Note: strings.json structure for entities is usually:
            # entity.<platform>.<translation_key>.name
            found = False
            for platform in ["sensor", "binary_sensor", "calendar"]:
                if f"entity.{platform}.{key}.name" in flat_strings:
                    found = True
                    break

            assert (
                found
            ), f"Translation key '{key}' from {os.path.basename(file_path)} missing in strings.json"


async def test_extra_translation_sections(strings_path, en_path, de_path):
    """Test consistency for extra translation sections like repairs, train_types."""
    with open(strings_path, "r", encoding="utf-8") as f:
        strings = json.load(f)
    with open(en_path, "r", encoding="utf-8") as f:
        en = json.load(f)
    with open(de_path, "r", encoding="utf-8") as f:
        de = json.load(f)

    # Check train_types keys (now in entity.sensor.departures.state)
    train_types_keys = [
        "s_bahn",
        "regional_db",
        "regional",
        "long_distance",
        "bus",
        "unknown",
    ]
    state_strings = (
        strings.get("entity", {})
        .get("sensor", {})
        .get("departures", {})
        .get("state", {})
    )
    if state_strings:
        for type_key in train_types_keys:
            assert (
                type_key in state_strings
            ), f"Missing strings.json translation for train_type {type_key} in state block"
            assert type_key in en.get("entity", {}).get("sensor", {}).get(
                "departures", {}
            ).get(
                "state", {}
            ), f"Missing EN translation for train_type {type_key} in state block"
            assert type_key in de.get("entity", {}).get("sensor", {}).get(
                "departures", {}
            ).get(
                "state", {}
            ), f"Missing DE translation for train_type {type_key} in state block"


async def test_all_translation_keys_referenced():
    """Test that all translation keys used in code are present in strings.json."""
    strings_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "db_infoscreen",
        "strings.json",
    )
    with open(strings_path, "r", encoding="utf-8") as f:
        strings = json.load(f)

    # 1. Check repairs action keys used in repairs.py
    repairs_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        DOMAIN,
        "repairs.py",
    )
    with open(repairs_path, "r", encoding="utf-8") as f:
        # SelectOptionDict(value="retry", label="retry")
        action_matches = re.findall(
            r'SelectOptionDict\(value="([^"]+)",',
            f.read(),
        )

    # All translated options from the selector block in strings.json
    translated_options = (
        strings.get("selector", {}).get("repair_action", {}).get("options", {})
    )

    for action_key in set(action_matches):
        if action_key in ["retry", "report", "change_source", "remove", "try_again"]:
            assert (
                action_key in translated_options
            ), f"Action key '{action_key}' from repairs.py missing in 'selector.repair_action.options' within strings.json"

    # 2. Check train type keys used in const.py
    const_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "custom_components",
        "db_infoscreen",
        "const.py",
    )
    with open(const_path, "r", encoding="utf-8") as f:
        const_content = f.read()

    mapping_match = re.search(
        r"TRAIN_TYPE_MAPPING = \{([^}]+)\}", const_content, re.DOTALL
    )
    if mapping_match:
        keys = re.findall(r': "([^"]+)"', mapping_match.group(1))
        valid_types = (
            strings.get("entity", {})
            .get("sensor", {})
            .get("departures", {})
            .get("state", {})
            .keys()
        )
        for key in keys:
            assert (
                key in valid_types
            ), f"Train type key '{key}' from const.py missing in strings.json['entity']['sensor']['departures']['state']"


async def test_translation_schema_compliance(strings_path, en_path, de_path):
    """Strictly validate schema compliance against March 2026 hassfest rules."""
    for path in [strings_path, en_path, de_path]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        def check_schema(obj, trace=""):
            if not isinstance(obj, dict):
                return

            # Rule 1: 'data' blocks in any flow step must contain ONLY strings (no nested dicts)
            if trace.endswith(".data"):
                for key, value in obj.items():
                    assert isinstance(
                        value, str
                    ), f"Schema Violation in {os.path.basename(path)}: '{trace}.{key}' must be a string, but got {type(value).__name__} (Dicts in 'data' blocks are forbidden)"

            # Rule 2: 'options' blocks are NOT ALLOWED in flow steps (caught by hassfest)
            # They must be in the top-level 'selector' block instead
            if trace.endswith(".step.init") or trace.endswith(".step.user"):
                assert (
                    "options" not in obj
                ), f"Schema Violation in {os.path.basename(path)}: '{trace}.options' is forbidden. Flow step options must be moved to the root 'selector' block."

            for key, value in obj.items():
                check_schema(value, f"{trace}.{key}" if trace else key)

        check_schema(data)

        # Rule 3: Custom state attribute values must not be nested under state_attributes
        entity_sensor = data.get("entity", {}).get("sensor", {})
        for sensor_id in entity_sensor:
            state_attrs = entity_sensor[sensor_id].get("state_attributes", {})
            for attr_id in state_attrs:
                val = state_attrs[attr_id]
                assert not isinstance(
                    val, dict
                ), f"Schema Violation in {os.path.basename(path)}: 'entity.sensor.{sensor_id}.state_attributes.{attr_id}' is a dictionary. Custom attribute values must be moved to the 'state' block."

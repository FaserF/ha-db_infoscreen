# AI Agent Reference: ha-db_infoscreen

## 1. Rules & Token Efficiency
- Output: Bullet points only (<=5 items for changes), no pleasantries/filler/narration, default English (EN).
- Code/Files: Targeted reads (`StartLine`/`EndLine`). Markdown links only, no code echo. No unrequested plans/walkthroughs.
- Tests/Linters: Report failures only. Run specific test files (`pytest tests/<test_file>.py`).

## 2. Architecture (`custom_components/db_infoscreen`)
- `__init__.py`: Setup, coordinator, unload handlers.
- `sensor.py`, `binary_sensor.py`, `calendar.py`: Entity platforms.
- `config_flow.py`: UI setup and options flow.
- `utils.py`, `const.py`: Helpers and constants.
- `strings.json`, `translations/`: UI strings (EN/DE).

## 3. Standards & Hygiene
- **Non-blocking Async**: All I/O asynchronous via `aiohttp` or `hass.async_add_executor_job`. Never block the event loop.
- **Hygiene**: No `raise e` (use `raise ... from e` or naked `raise`). `except: pass` forbidden.
- **Translations**: Mirror `strings.json` changes into `translations/de.json` and `translations/en.json`.

## 4. CLI Commands
- Test: `pytest tests/test_sensor.py`
- Lint: `ruff check . --fix && mypy .`

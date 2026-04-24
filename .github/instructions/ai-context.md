# AI Context & Instructions for ha-db_infoscreen

## 🧬 Project DNA
**Repository:** `ha-db_infoscreen`
**Type:** Home Assistant Custom Integration
**Domain:** `db_infoscreen`
**Description:** DB-Infoscreen for Home Assistant 🚆 A comprehensive departure board integration for Home Assistant.

## 🛠 Tech Stack & Standards
- **Core Languages:** Python (Async/Await), Home Assistant Core API
- **Toolchain:** Pytest, MyPy (Strict Typing)
- **Dependencies:** None specified

## 📐 Coding Guidelines (Home Assistant Context)
- **Architecture:** Must adhere to modern Home Assistant architecture guidelines (`config_flow`, `coordinator`, `entity`).
- **Typing:** Strict typing is enforced. Use `mypy` annotations and avoid `Any`.
- **Asynchronous Patterns:** Operations must be non-blocking. Use `asyncio` and `aiohttp` for I/O operations. Do not use `requests` or blocking time sleeps.
- **Naming Conventions:** Follow PEP 8. Prefix internal variables appropriately. Use English for all logging and documentation.
- **Error Handling:** Use `UpdateFailed` for coordinator errors, and cleanly handle connection timeouts without logging sensitive credentials.

## 🤖 Tool-Specific Optimization

### 🐙 GitHub Copilot
- **Code Generation:** When generating entity definitions, ensure they inherit from standard HA classes (e.g., `CoordinatorEntity`). 
- **Boilerplate:** Match the existing structure of the file. Do not invent new configuration schemas if `cv.schema` or `voluptuous` are already imported.

### 🧠 Claude Code
- **Refactoring & Complex Tasks:** Before executing changes, review `__init__.py` and `manifest.json`. Map out the data flow from `config_flow` -> `Coordinator` -> `Entities`.
- **Validation:** Always verify imports and type safety. If proposing a fix for a state error, trace the variable back to the API response.

### 🚀 Google Antigravity
- **Codebase Navigation:** Begin by analyzing `custom_components/db_infoscreen/`. Search for established patterns in `api.py` or `coordinator.py` before modifying entities.
- **Testing Requirements:** When modifying logic, run or propose tests matching the existing `tests/` directory structure. 

## 🧪 Test Procedures
- **Execution:** Use `pytest` via `pytest.ini` or `Makefile`.
- **Coverage:** Mock network requests using `aioresponses` or `pytest-httpx`. Never make live API calls in tests.

## 🚫 Exclusion Rules
- **NEVER MODIFY:**
  - `translations/` (unless specifically asked to add a new string)
  - `hacs.json` (managed via CI/CD or strictly manually)
  - `.github/workflows/` (CI pipelines are considered stable)

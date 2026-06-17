# AI Agent Reference for ha-db_infoscreen

---

## Token Efficiency Rules (CRITICAL — Read First)

These rules apply to **every response** without exception:

1. **Output minimal prose.** Bullet points only. No introductory sentences, no filler, no "Great question!", no "As requested".
2. **No walkthrough unless explicitly asked.** Never create or update `walkthrough.md` unless the user writes "walkthrough" or "summary" in their request.
3. **No implementation plan unless complex.** Skip planning artifacts for simple tweaks, single-file edits, bug fixes, or minor features. Plan only for major architectural changes.
4. **Short change summaries only.** After making changes, output ≤5 bullet points describing *what* changed and *why* — never a line-by-line description.
5. **No repeating file content.** Never echo back code you just wrote or edited. Reference filenames with links instead.
6. **No tool-call narration.** Do not describe what tool you are about to call. Just call it.
7. **Targeted file reads only.** Use `grep_search` or `view_file` with `StartLine`/`EndLine` to read only the relevant section. Never view an entire large file unless strictly necessary.
8. **Parallel tool calls.** Fire all independent tool calls in a single block. Never sequence calls that can run simultaneously.
9. **No re-summarizing artifacts.** After creating or updating an artifact, do NOT restate its contents — just link to it and note any open questions.
10. **Skip trivial confirmations.** Do not ask "Would you like me to proceed?" for obvious next steps. Just do them.
11. **No closing pleasantries.** End your response after the change summary. No "Let me know if you have questions!" etc.
12. **Reuse subagents.** Send follow-up tasks to an existing idle subagent instead of spawning a new one.
13. **Suppress test output noise.** When running pytest, only report failures. Do not paste successful test output unless the user asks.
14. **Delegate with subagents.** For any research-heavy, multi-file, or parallelizable task, spin up a subagent instead of doing it inline.
15. **Prefer `research` subagent for read-only work.** Codebase exploration, grep searches, file reads, and web lookups should go to the `research` subagent.
16. **Prefer `self` subagent for isolated execution.** Use the `self` subagent for tasks that need write access in a separate context.
17. **Don't poll subagents.** After launching a subagent, stop calling tools. The system wakes you automatically.

---

## Codebase Architecture

### Home Assistant Integration Component (`/custom_components/db_infoscreen`)

| Area | Path |
|---|---|
| Main entry & Setup | `custom_components/db_infoscreen/__init__.py` |
| Sensor platform | `custom_components/db_infoscreen/sensor.py` |
| Binary Sensor platform | `custom_components/db_infoscreen/binary_sensor.py` |
| Calendar platform | `custom_components/db_infoscreen/calendar.py` |
| Config Flow (UI setup) | `custom_components/db_infoscreen/config_flow.py` |
| Translation strings | `custom_components/db_infoscreen/translations/` |
| Helper Utilities | `custom_components/db_infoscreen/utils.py` |
| Integration Constants | `custom_components/db_infoscreen/const.py` |

---

## CLI Commands

| Task | Command | Dir |
|---|---|---|
| Run all tests | `pytest` | Root |
| Run specific test file | `pytest tests/test_sensor.py` | Root |
| Ruff linter check | `ruff check .` | Root |
| Ruff linter auto-fix | `ruff check . --fix` | Root |
| mypy type checker | `mypy .` | Root |

---

## Coding Rules & Quality Guidelines

- **Async Database & API patterns**: Ensure all network and API calls inside coordinator/sensors are handled asynchronously without blocking the Home Assistant event loop. Use `async_add_executor_job` for blocking synchronous calls.
- **Translation integrity**: When adding or updating config flow/sensor strings, update both `strings.json` and the corresponding translation files in `translations/` (e.g. `de.json`, `en.json`).
- **Traceback Preservation**: NEVER use `raise e`. ALWAYS use `raise ... from e` or a naked `raise` to prevent stack trace destruction.
- **Silent Failure Prohibition**: `except: pass` is FORBIDDEN. All exceptions must be wrapped and propagated, or logged with context using `_LOGGER`.
- **Testing**: Run pytest only for affected test files. Only report failure output to save token context.

---

## Script Rules

- **Temporary scripts & files** (one-off, session-only use): place in `/scratch/` at repo root. Never commit these.
- **Reusable scripts**: place in `/scripts/` — never in the repo root directory.
- **No credentials in reusable scripts**: read secrets, tokens, or environment-specific values from environment variables or Home Assistant configuration.

---

## Language Rules

- **Codebase & Documentation**: All program code, docs, and inline comments must always be written in English (EN).
- **AI Chat Interactions**: Respond in German (DE) if the user communicates in German; otherwise default to English (EN).

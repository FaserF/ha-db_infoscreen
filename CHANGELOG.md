# Changelog

## 2026.1.0

### ✨ New Features
*   **Excluded Directions**: Added a new configuration option `excluded_directions` to filter out departures heading to specific destinations (substring match).

### 🐛 Bug Fixes
*   **Parsing**: Fixed an issue where `trainClasses` were incorrectly parsed for some providers (e.g., VRN), converting strings like "Bus" into character lists `['B', 'u', 's']`.
*   **Mappings**: Added a fallback for "Unknown" train types to ensure better display names.

### 📚 Documentation
*   **Readme**: Updated documentation to include the new `excluded_directions` option and clarify existing configuration parameters.

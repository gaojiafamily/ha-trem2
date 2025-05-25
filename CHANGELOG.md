# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.2.0] - 2025/05/25
### Added
  - Added select entity to view the latest 5 earthquake report records.
  - Added ExpTech VIP feature with WebSocket support.
  - Added diagnostic functionality to the configuration menu.
  - Added provider option to the configuration flow.
  - Added Japanese and Simplified Chinese fonts (Noto Sans).
  - Added binary sensor for vibrate notifications.

### Refactor & Improvements
  - Introduced runtime.py to centralize runtime data management, including classes such as ExpTechClient and Trem2RuntimeData.
  - Refactored sensor.py to use the new runtime structure, improving entity management and state updates.
  - Implemented store.py for efficient data processing and storage, including recent and report data handling.
  - Updated update_coordinator.py to integrate the new store and runtime classes, enhancing data retrieval and management.
  - Removed deprecated code and streamlined the update process for both HTTP and WebSocket clients.
  - Adjusted service registration in services.py to align with the new data structure.
  - Updated services.yaml to reflect the revised simulation data format.
  - Refactored update services, translations, and data handling.
  - Refactored complex logic using match-case and method splitting to comply with flake8.
  - Introduced new classes for managing TREM state and configuration, improving code organization and readability.
  - Changed entity setup to use AddEntitiesCallback as recommended by Home Assistant.

### Other Improvements
  - Enhanced runtime data management and type safety.
  - Added Terms of Service agreement check and updated translations.
  - Improved error logging, diagnostics handling, and intensity calculation logic.
  - Enhanced error handling for HTTP and WebSocket clients and improved diagnostics output.
  - Improved configuration flow and enhanced error handling.
  - Enhanced English and Traditional Chinese translations for configuration flow, including re-authentication messages and descriptions.
  - Updated map display to show epicenter lat/long if offshore.

### Fix
  - Fixed issue where reports were not up to date.
  - Fixed websocket not disconnecting when the integration is unloaded.
  - Updated logic for handling earthquake and report data to ensure better fallback mechanisms and data integrity.


## [1.1.2] - 2025/04/22

### Added
- ImageEntity extra_attr add TREM report image url.
- `set_http_node` and `set_ws_node` in services, To set specified server URL by the user.


### Fix
- Service: save2file default using serail.
- Report intensity mapping incorrect.

### Refactor & Improvements
- Add connection validation and backoff logic.


## [1.1.1] - 2025/04/16

### Fix
- Config flow not showing issue.
- EPICenter depth information incorrect.

### Refactor & Improvements
- Improve report presentation.


## [1.1.0] - 2025/04/14

### Added
- Functionality for simulating earthquakes and saving images generated during simulations.

### Fix
- Resolved QR Code invalidity issue by adjusting encoding logic.

### Breaking changes
- implement multiple improvements across caching, actions, templates, and code formatting

### Removed
- Remove system-level dependencies (cairosvg with pyvips for efficient SVG-to-PNG rendering).

### Refactor & Improvements
- Improve font install: Copy Chinese font (NotoSansTC-Regular.ttf) to user font directory.
- Reformatted code to comply with Flake8 and PEP8 guidelines.


## [1.0.0] - 2025/04/07

### Added
- Initial commit

[1.2.0]: https://github.com/gaojiafamily/ha-trem2/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/gaojiafamily/ha-trem2/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/gaojiafamily/ha-trem2/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/gaojiafamily/ha-trem2/compare/v1.0.0...v1.1.0
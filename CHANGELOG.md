# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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


[1.1.0]: https://github.com/gaojiafamily/ha-trem2/compare/v1.0.0...v1.1.0
[1.1.1]: https://github.com/gaojiafamily/ha-trem2/compare/v1.1.0...v1.1.1
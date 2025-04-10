# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.1.2] - Unreleased

### Fixed

- Fixes process name display in log messages by appending the `.exe` extension, ensuring you know exactly which process is ignoring your desperate attempts to save.

## [0.1.1] (2025-04-09)

### Changed

- Improves config file handling by using `PolyPath` for standardized access across platforms, so your settings won't mysteriously vanish anymore.
- Renames package from `starfield_saver` to `starfieldsaver` for consistency, because underscores are so 2024.
- Updates `polykit` dependency from 0.9.0 to 0.9.1, making things marginally better in ways you'll never notice.
- Adds Windows platform check in `main.py`, politely telling non-Windows users they're out of luck.

## [0.1.0] (2025-04-08)

### Changed

- Resets application version to 0.1.0 for official publishing to PyPI.
- Adds MIT license and updates project metadata, legally allowing you to do almost anything with the code except blame the author when things go wrong.

### Removed

- Removes auto-update functionality, because we don't distribute EXEs anymore. That's just unsafe.
- Removes dsutil submodule, because it's ancient and we use [polykit](https://github.com/dannystewart/polykit) now.

<!-- Links -->
[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[unreleased]: https://github.com/dannystewart/starfield-saver/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/dannystewart/starfield-saver/releases/tag/v0.1.2
[0.1.1]: https://github.com/dannystewart/starfield-saver/compare/v0.1.0...v0.1.1

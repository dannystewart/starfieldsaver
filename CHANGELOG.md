# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.2.0] (2025-04-11)

### Added

- Adds comprehensive README documentation with installation instructions, configuration examples, usage explanations, and troubleshooting tips.

### Changed

- Renames `QuicksaveUtility` to `StarfieldQuicksaver` and moves its code to `main.py` for simpler organization.
- Changes config file name to `starfieldsaver.toml` from `config.toml` for better namespacing.
- Simplifies configuration options with shorter, more intuitive names:
  - `save_directory` → `save_dir`
  - `status_check_interval` → `check_interval`
  - `enable_quicksave_on_interval` → `enable_quicksave`
  - `enable_copy_to_regular_save` → `copy_to_regular_save`
  - `prune_saves_older_than` → `prune_older_than_days`
- Converts `SaveType` from `Enum` to `StrEnum` for more readable code.
- Improves process name handling by centralizing logic and moving `.exe` suffix handling to initialization.
- Updates PyInstaller build output path from root directory to `dist` folder
- Adds project classifiers with metadata about development status, environment, and supported Python versions.

### Removed

- Removes unimplemented config settings, including `info_volume` and `error_volume` (use `enable_success_sounds` instead) as well as `enable_save_cleanup` (redundant to `prune_older_than_days` being greater than zero).
- Removes Windows executable from distribution. Install via `pip` or grab from the Releases page instead.

### Fixed

- Fixes process focus logging to include the `.exe` extension for clarity and because Windows needs to be reminded everything's an executable.

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
[unreleased]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/dannystewart/starfieldsaver/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/dannystewart/starfieldsaver/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dannystewart/starfieldsaver/releases/tag/v0.1.0

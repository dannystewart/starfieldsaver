# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.2.0] (2025-04-11)

### Changed

- Renames `QuicksaveUtility` to `StarfieldQuicksaver` and moves its code to `main.py` for simpler organization.
- Simplifies configuration options with shorter, more intuitive names:
  - `save_directory` → `save_dir`
  - `status_check_interval` → `check_interval`
  - `enable_quicksave_on_interval` → `enable_quicksave`
  - `enable_copy_to_regular_save` → `copy_to_regular_save`
  - `prune_saves_older_than` → `prune_older_than`
- Converts `SaveType` from `Enum` to `StrEnum` for more readable code.
- Adds project classifiers with metadata about development status, environment, and supported Python versions.

### Removed

- Removes Windows batch file (`starfield_saver.bat`) and executable (`starfield_saver.exe`) from distribution—now you'll need to install via pip like a proper Constellation agent.
- Removes some unimplemented configuration options, including `info_volume` and `error_volume` (use `enable_success_sounds` instead) as well as `enable_save_cleanup` (redundant to `prune_older_than` being greater than zero).

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
[0.1.1]: https://github.com/dannystewart/starfieldsaver/releases/tag/v0.1.1

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.2.4] (2025-04-11)

### Fixed

- Fixes `polykit` version constraint. No other changes.

## [0.2.3] (2025-04-11)

### Added

- Adds improved config file discovery with proper precedence, supporting packaged executables and prioritizing the current directory for both existing and new configs.
- Adds validation of the save directory on startup, failing early with a clear error message if the directory doesn't exist.

### Changed

- Restructures the codebase by moving the `StarfieldQuicksaver` class to its own module and creating a dedicated `types` module to keep things better organized.
- Updates `.gitignore` to exclude TOML files while specifically allowing `ruff.toml` to keep the linting config accessible without getting config files.

### Fixed

- Fixes Windows path format in README by using double backslashes instead of single backslashes to comply with TOML syntax requirements.
- Fixes heading levels in `CHANGELOG.md`.

### Removed

- Removes troubleshooting section from README as it was effectively redundant.

## [0.2.2] (2025-04-11)

### Changed

- Renames `process_name` config variable to `game_exe` for better clarity and consistency.

### Removed

- Removes GitHub Pages documentation workflow, because it was causing problems for the sake of documentation that didn't exist anyway.

### Fixed

- Improves `pynput` import error handling on non-Windows platforms.
- Fixes conditional importing of `pynput.keyboard` to prevent errors on non-Windows platforms.
- Corrects game process name assignment when appending `.exe` extension.

## [0.2.1] (2025-04-11)

### Added

- Adds GitHub workflow for automatic publishing to PyPI when version tags are pushed.

### Fixed

- Fixes application crashes on non-Windows platforms by moving platform check before `pynput` imports, ensuring a graceful exit instead of a dramatic meltdown when running on unsupported operating systems.

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
[unreleased]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/dannystewart/starfieldsaver/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/dannystewart/starfieldsaver/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/dannystewart/starfieldsaver/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dannystewart/starfieldsaver/releases/tag/v0.1.0

# Starfield Saver

A utility to automatically quicksave in Starfield on a specified interval, as well as back them up by duplicating them to regular saves so they aren't overwritten by subsequent quicksaves. Also supports autosaves.

## Configuration

Many settings are configurable via the `config.toml` config file:

- `save_directory`: Directory where save files are stored.
- `process_name`: Name of the game process to monitor (without extension).
- `check_interval`: Time between checks (in seconds).
- `quicksave_save`: Whether to create quicksaves.
- `quicksave_interval`: Time between quicksaves (in seconds).
- `quicksave_copy`: Whether to copy quicksaves to regular saves.
- `days_before_pruning_saves`: Number of days before pruning saves to one per day (0 to keep all).
- `save_cleanup_dry_run`: Whether to perform a dry run of save cleanup.
- `enable_sounds`: Whether to play sounds on events.
- `info_volume`: Volume for info sounds (0.0 to 1.0).
- `error_volume`: Volume for error sounds (0.0 to 1.0).
- `color_log`: Whether to use color in logging.
- `debug_log`: Whether to enable debug logging.

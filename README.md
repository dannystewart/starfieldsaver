# Starfield Saver

A utility to automatically quicksave in Starfield on a specified interval, as well as back them up by duplicating them to regular saves so they aren't overwritten by subsequent quicksaves. Also supports autosaves.

## Configuration

Many settings are configurable via the `config.toml` config file:

- `save_dir`: Directory where save files are stored.
- `process_name`: Name of the game process to monitor.
- `enable_quicksave`: Whether to create quicksaves.
- `check_interval`: Time between checks (in seconds).
- `quicksave_every`: Time between quicksaves (in seconds).
- `copy_to_regular_save`: Whether to copy quicksaves to regular saves.
- `prune_older_than`: Number of days before pruning saves to one per day (0 to keep all).
- `dry_run`: Whether to perform a dry run of save cleanup.
- `enable_sounds`: Whether to play sounds on events.
- `enable_debug`: Whether to enable debug logging.

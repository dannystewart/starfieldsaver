# Starfield Quicksaver

An automatic quicksave utility for Starfield that helps prevent lost progress and manages your save files.

## Features

- **Automatic Quicksaving**: Creates quicksaves at configurable intervals while playing.
- **Save Conversion**: Automatically converts quicksaves and autosaves to regular saves.
- **Save Management**: Intelligently prunes old saves while preserving one save per day.
- **Non-Intrusive**: Only runs when Starfield is active and in focus.
- **Audio Feedback**: Optional sound notifications for save events.
- **Configurable**: Easy to customize via config file.

## Installation

1. Download the latest release from the [Releases page](https://github.com/dannystewart/starfieldsaver/releases)
2. Extract to a location of your choice
3. Run `starfieldsaver.exe`

The first time you run the application, it will create a `starfieldsaver.toml` default configuration file.

## Configuration

Configuration is stored in `starfieldsaver.toml` in the application directory. You can modify this file directly or through the application interface.

### Basic Configuration Options

```toml
[paths]
save_dir = "C:/Users/YourUsername/Documents/My Games/Starfield/Saves"
game_exe = "Starfield.exe"

[saves]
enable_quicksave = true
check_interval = 10
quicksave_every = 240
copy_to_regular_save = true
enable_success_sounds = true

[cleanup]
prune_older_than_days = 0
dry_run = true

[logging]
enable_debug = false
```

### Configuration Details

#### Paths

- `save_dir`: Directory where Starfield saves are stored
- `game_exe`: Name of the game process to monitor (with or without .exe)

#### Saves

- `enable_quicksave`: Whether to enable automatic quicksaving (true/false).
- `check_interval`: How often to check game status in seconds.
- `quicksave_every`: Time between automatic quicksaves in seconds (default: 4 minutes).
- `copy_to_regular_save`: Whether to copy quicksaves to regular saves (true/false).
- `enable_success_sounds`: Whether to play sound notifications for successful saves (true/false). Note that error sounds will always play.

#### Cleanup

- `prune_older_than_days`: Number of days before pruning saves to one per day (0 to disable)
- `dry_run`: Test cleanup without deleting files (true/false)

#### Logging

- `enable_debug`: Enable detailed debug logging (true/false)

## How It Works

1. The utility monitors your game session and automatically creates quicksaves at your configured interval.
2. When a quicksave or autosave is detected, it's copied to a regular save with proper naming.
3. The utility only runs when Starfield is in focus to avoid interfering with other applications.
4. Old saves can be automatically cleaned up, keeping one save per day for saves older than your configured threshold.

## Save Cleanup

When enabled, the save cleanup feature:

- Preserves all saves newer than the specified number of days.
- For older saves, keeps one save per day per character.
- Always preserves your most recent saves.
- Can run in "dry run" mode to show what would be deleted without actually removing files.

## Sound Notifications

The utility provides audio feedback for successful saves, manual quicksaves detected, and if an error occurs.

- Success sound: When a save is successfully created.
- Notification sound: When a manual quicksave is detected.
- Error sound: If an error occurs.

You can use the `enable_success_sounds` config option to disable success and notification sounds to avoid disrupting your immersion.

**NOTE:** Error sounds will always play, so you'll know when something has gone wrong and your game may not have saved correctly.

## Troubleshooting

- **Game not detected**: Ensure the correct `game_exe` is set in starfieldsaver.toml.
- **Saves not detected**: Verify the `save_dir` path is correct.
- **No sounds**: Check that `enable_success_sounds` is set to true.

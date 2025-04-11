from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import toml
from watchdog.events import (
    DirModifiedEvent,
    DirMovedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)

if TYPE_CHECKING:
    from starfieldsaver.quicksaver import StarfieldQuicksaver


def get_config_file() -> Path:
    """Get the configuration file path with appropriate precedence."""
    config_filename = "starfieldsaver.toml"

    # Check if running as executable
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent / config_filename

    # Check current directory first (most accessible)
    cwd_config = Path(config_filename)
    if cwd_config.exists():
        return cwd_config

    # If we need to create a new config, use current directory
    return cwd_config


@dataclass
class QuicksaveConfig:
    """Configuration for behavior of the quicksave utility.

    Attributes:
        save_dir: Directory where save files are stored.
        game_exe: Name of the game process to monitor.
        check_interval: Time between status checks (in seconds).
        quicksave_every: Time between quicksaves (in seconds).
        enable_quicksave: Whether to enable quicksaving on the set interval.
        copy_to_regular_save: Whether to copy quicksaves to regular saves.
        prune_older_than_days: Number of days before pruning saves to one per day (0 to keep all).
        dry_run: Whether to perform a dry run of save cleanup (log only).
        enable_success_sounds: Whether to play sounds on events.
        enable_debug: Whether to enable debug logging.
    """

    save_dir: str
    game_exe: str = "Starfield.exe"
    enable_quicksave: bool = True
    check_interval: float = 10
    quicksave_every: float = 240
    copy_to_regular_save: bool = True
    prune_older_than_days: int = 0
    dry_run: bool = True
    enable_success_sounds: bool = True
    enable_debug: bool = False
    extra_config: dict[str, Any] = field(default_factory=dict)

    # Define the structure of the TOML file
    config_structure: ClassVar[dict[str, list[str]]] = {
        "paths": ["save_dir", "game_exe"],
        "saves": [
            "enable_quicksave",
            "check_interval",
            "quicksave_every",
            "copy_to_regular_save",
            "enable_success_sounds",
        ],
        "cleanup": ["prune_older_than_days", "dry_run"],
        "logging": ["enable_debug"],
    }

    def __post_init__(self):
        # Append .exe to filename if not already present
        self.game_exe = (
            f"{self.game_exe}.exe" if not self.game_exe.endswith(".exe") else self.game_exe
        )

        # Get any additional config items not in the annotations
        self.extra_config = {
            k: v for k, v in self.__dict__.items() if k not in self.__annotations__
        }
        for k in self.extra_config:
            delattr(self, k)


class ConfigLoader:
    """Class for loading and saving the quicksave configuration."""

    MAX_RETRIES: ClassVar[int] = 3
    RETRY_DELAY: ClassVar[float] = 0.1

    @classmethod
    def load(cls) -> QuicksaveConfig:
        """Load the configuration from the TOML file or create a new one.

        Raises:
            toml.TomlDecodeError: If the configuration file is malformed.
        """
        config_file = get_config_file()

        for attempt in range(cls.MAX_RETRIES):
            try:
                if not config_file.exists():
                    return cls._create_default_config()

                with config_file.open(encoding="utf-8") as f:
                    config_data = toml.load(f)

                return cls._process_config(config_data)

            except toml.TomlDecodeError:
                if attempt < cls.MAX_RETRIES - 1:
                    time.sleep(cls.RETRY_DELAY)
                else:
                    raise

        return cls._create_default_config()

    @classmethod
    def reload(cls, current_config: QuicksaveConfig, logger: logging.Logger) -> QuicksaveConfig:
        """Reload the configuration from the TOML file."""
        try:
            new_config = cls.load()
            if current_config.enable_debug != new_config.enable_debug:
                cls._update_logger_level(logger, new_config.enable_debug)
            logger.info("Reloaded config due to modification on disk.")
            return new_config
        except Exception as e:
            logger.warning(
                "Failed to reload config after multiple attempts: %s. Continuing with previous config.",
                str(e),
            )
            return current_config

    @staticmethod
    def _update_logger_level(logger: logging.Logger, debug: bool) -> None:
        new_level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(new_level)
        for handler in logger.handlers:
            handler.setLevel(new_level)
        logger.info("Logger level updated to %s.", "debug" if debug else "info")

    @classmethod
    def _process_config(cls, config_data: dict[str, Any]) -> QuicksaveConfig:
        # Flatten the sectioned config
        flat_config = {}
        for section, values in config_data.items():
            if section in QuicksaveConfig.config_structure:
                flat_config |= values
            else:
                flat_config[section] = values

        known_attrs = {
            k: flat_config.pop(k) for k in QuicksaveConfig.__annotations__ if k in flat_config
        }
        config = QuicksaveConfig(**known_attrs)
        config.extra_config = flat_config

        # Check for missing attributes and add them with default values
        default_config = QuicksaveConfig(save_dir=config.save_dir)
        updated = False
        for attr, value in default_config.__dict__.items():
            if attr not in known_attrs and attr != "extra_config":
                setattr(config, attr, value)
                updated = True

        if updated:
            cls._save_config(config)

        return config

    @classmethod
    def _save_config(cls, config: QuicksaveConfig) -> None:
        config_file = get_config_file()

        config_dict = {
            section: {k: getattr(config, k) for k in keys}
            for section, keys in QuicksaveConfig.config_structure.items()
        }
        if config.extra_config:
            config_dict["extra"] = config.extra_config

        with config_file.open("w", encoding="utf-8") as f:
            toml.dump(config_dict, f)

    @classmethod
    def _create_default_config(cls) -> QuicksaveConfig:
        quicksave_folder = Path("~/Documents/My Games/Starfield/Saves").expanduser()
        config = QuicksaveConfig(str(quicksave_folder))
        cls._save_config(config)
        return config


class ConfigFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the quicksave configuration file."""

    def __init__(self, quicksave_utility: StarfieldQuicksaver):
        self.saver = quicksave_utility
        self.config_file = str(get_config_file())

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        """Reload the configuration when the file is modified."""
        if not event.is_directory and str(event.src_path).endswith(self.config_file):
            self.saver.reload_config()


class SaveFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the save directory."""

    def __init__(self, quicksave_utility: StarfieldQuicksaver):
        self.saver = quicksave_utility

    def on_moved(self, event: FileMovedEvent | DirMovedEvent) -> None:
        """Handle a file move in the save directory."""
        self.saver.logger.debug(
            "Move event detected: %s -> %s",
            Path(str(event.src_path)).name,
            Path(str(event.dest_path)).name,
        )

        if not event.is_directory and str(event.dest_path).endswith(".sfs"):
            if self.saver.config.copy_to_regular_save:
                self.saver.new_game_save_detected(str(event.dest_path))
        else:
            self.saver.logger.debug("Moved file is not a game save, ignoring.")

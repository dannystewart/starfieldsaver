# ruff: noqa: T201

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import win32api  # type: ignore
import win32con  # type: ignore
import win32gui  # type: ignore
import win32process  # type: ignore
from pynput.keyboard import Controller, Key
from zoneinfo import ZoneInfo

from dsutil.files import copy_file, list_files
from dsutil.log import LocalLogger

tz = ZoneInfo("America/New_York")

logger = None


@dataclass
class Config:
    """
    Configuration for the quicksave behavior.

    Attributes:
        save_directory: Directory where save files are stored
        process_name: Name of the game process to monitor (without extension)
        update_interval: Time between checks (in seconds)
        quicksave_save: Whether to create quicksaves
        quicksave_save_interval: Time between quicksaves (in seconds)
        quicksave_copy: Whether to copy quicksaves to regular saves
    """

    save_directory: str
    process_name: str = "Starfield"
    update_interval: float = 10.0
    quicksave_save: bool = True
    quicksave_save_interval: float = 240.0
    quicksave_copy: bool = True


def setup_logger(debug: bool = False) -> None:
    """Set up the logger with the specified debug level."""
    global logger

    level = logging.DEBUG if debug else logging.INFO
    logger = LocalLogger.setup_logger("starfield_quicksave", level=level)


def load_config() -> Config:
    """Load the configuration from a JSON file or create a new one."""
    global logger

    config_path = "quicksave.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = Config(**json.load(f))
    else:
        config = Config(
            os.path.join(os.path.expanduser("~"), "Documents", "My Games", "Starfield", "Saves")
        )
        with open(config_path, "w") as f:
            json.dump(config.__dict__, f, indent=2)

    logger.debug("Configuration loaded with settings:")
    for key, value in asdict(config).items():
        logger.debug("  %s: %s", key, value)

    return config


def get_foreground_process_name() -> str:
    """Get the name of the process that is currently in focus."""
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = win32api.OpenProcess(
        win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
    )
    try:
        process_path = win32process.GetModuleFileNameEx(handle, 0)
        return os.path.basename(process_path)
    finally:
        win32api.CloseHandle(handle)


def is_target_process_active(config: Config) -> bool:
    """Check if the target process is in focus."""
    global logger

    foreground_process = get_foreground_process_name()
    logger.debug("Current foreground process: %s", foreground_process)
    if not foreground_process.lower().startswith(config.process_name.lower()):
        logger.debug("Skipping because %s.exe was not in focus.", config.process_name)
        return False
    logger.debug("%s.exe is in focus, checking quicksave status.", config.process_name)
    return True


def create_quicksave(
    config: Config,
    keyboard: Controller,
    last_quicksave_time: datetime | None,
) -> datetime:
    """Create a new quicksave."""
    global logger

    current_time = datetime.now(tz=tz)
    if last_quicksave_time is None or (current_time - last_quicksave_time) >= timedelta(
        seconds=config.quicksave_save_interval
    ):
        logger.info("Creating new quicksave.")
        keyboard.press(Key.f5)
        time.sleep(0.2)
        keyboard.release(Key.f5)
        return current_time
    return last_quicksave_time


def copy_quicksave(config: Config, last_copy_time: datetime | None) -> tuple[datetime, bool]:
    """Copy the latest quicksave if it is newer than the last copied quicksave."""
    global logger

    latest_quicksave = find_latest_quicksave(config)
    if latest_quicksave is None:
        logger.warning("No quicksave files found.")
        return last_copy_time, False

    quicksave_file, quicksave_time = latest_quicksave
    if last_copy_time is None or quicksave_time > last_copy_time:
        copy_quicksave_to_regular_save(config, quicksave_file)
        return quicksave_time, True

    return last_copy_time, False


def find_latest_quicksave(config: Config) -> tuple[str, datetime] | None:
    """Find the latest quicksave file."""
    quicksaves = list_files(
        config.save_directory,
        extensions=["sfs"],
        sort_key=lambda x: x.stat().st_mtime,
        reverse_sort=True,
    )
    return next(
        (
            (
                str(quicksave),
                datetime.fromtimestamp(os.path.getmtime(quicksave), tz=tz),
            )
            for quicksave in quicksaves
            if os.path.basename(quicksave).startswith("Quicksave0")
        ),
        None,
    )


def copy_quicksave_to_regular_save(config: Config, source: str) -> None:
    """Copy the quicksave to a new file."""
    global logger

    save_files = list_files(config.save_directory, extensions=["sfs"])
    highest_save_id = max(
        [
            int(os.path.basename(f).split("_")[0][4:])
            for f in save_files
            if os.path.basename(f).startswith("Save")
        ]
        + [0]
    )
    new_save_id = highest_save_id + 1
    destination = os.path.join(
        config.save_directory,
        f"Save{new_save_id}_{datetime.now(tz=tz).strftime('%Y%m%d%H%M%S')}.sfs",
    )
    copy_file(source, destination)
    logger.info(
        "Copied quicksave %s to %s.",
        os.path.basename(source),
        os.path.basename(destination),
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Starfield Quicksave Utility")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    """Quicksave on interval."""
    global logger

    args = parse_arguments()
    setup_logger(args.debug)
    logger.debug("Debug logging enabled.")

    config = load_config()
    keyboard = Controller()
    last_copy_time = None
    last_quicksave_time = None

    logger.info("Started quicksave utility for %s.", config.process_name)

    while True:
        try:
            time.sleep(config.update_interval)

            if not is_target_process_active(config):
                continue

            if config.quicksave_save:
                last_quicksave_time = create_quicksave(config, keyboard, last_quicksave_time)

            if config.quicksave_copy:
                last_copy_time, _ = copy_quicksave(config, last_copy_time)

        except KeyboardInterrupt:
            logger.info("Exiting quicksave utility.")
            break
        except Exception as e:
            logger.error("An error occurred: %s", str(e))


if __name__ == "__main__":
    main()

# ruff: noqa: T201

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import win32gui  # type: ignore
import win32process  # type: ignore
from pynput.keyboard import Controller, Key
from zoneinfo import ZoneInfo

from dsutil.files import copy_file, list_files
from dsutil.log import LocalLogger

tz = ZoneInfo("America/New_York")

logger = LocalLogger.setup_logger("starfield_quicksave")


@dataclass
class Config:
    """Configuration for the quicksave behavior."""

    save_directory: str
    process_name: str = "Starfield"
    update_interval: float = 10.0
    quicksave_save: bool = True
    quicksave_save_interval: float = 120.0
    quicksave_copy: bool = True


def load_config() -> Config:
    """Load the configuration from a JSON file or create a new one."""
    config_path = "quicksave.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            return Config(**json.load(f))
    else:
        config = Config(
            os.path.join(os.path.expanduser("~"), "Documents", "My Games", "Starfield", "Saves")
        )
        with open(config_path, "w") as f:
            json.dump(config.__dict__, f, indent=2)
        return config


def get_foreground_process_name() -> str:
    """Get the name of the process that is currently in focus."""
    hwnd = win32gui.GetForegroundWindow()
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return win32process.GetModuleFileNameEx(win32process.OpenProcess(0x1000, False, pid), 0)


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


def copy_quicksave(config: Config, source: str) -> None:
    """Copy the quicksave to a new file."""
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
        f"Save{new_save_id}_{datetime.now(tz=tz).strftime("%Y%m%d%H%M%S")}.sfs",
    )
    copy_file(source, destination)
    logger.info("Copied quicksave to %s.", destination)


def main() -> None:
    """Quicksave on interval."""
    config = load_config()
    keyboard = Controller()
    last_copy_time = None

    while True:
        try:
            time.sleep(config.update_interval)

            if get_foreground_process_name() != config.process_name:
                logger.debug("Skipping because %s was not in focus.", config.process_name)
                continue

            latest_quicksave = find_latest_quicksave(config)
            if latest_quicksave is None:
                logger.warning("No quicksave files found.")
                continue

            quicksave_file, quicksave_time = latest_quicksave

            # Handle quicksave copying
            if config.quicksave_copy and (
                last_copy_time is None or quicksave_time > last_copy_time
            ):
                copy_quicksave(config, quicksave_file)
                last_copy_time = quicksave_time

            # Handle quicksave creation
            if config.quicksave_save:
                time_since_last_quicksave = datetime.now(tz=tz) - quicksave_time
                if time_since_last_quicksave >= timedelta(seconds=config.quicksave_save_interval):
                    logger.info("Creating new quicksave")
                    keyboard.press(Key.f5)
                    time.sleep(0.2)
                    keyboard.release(Key.f5)

        except KeyboardInterrupt:
            logger.info("Quicksave utility stopped by user.")
            break
        except Exception as e:
            logger.error("An error occurred: %s", str(e))


if __name__ == "__main__":
    main()

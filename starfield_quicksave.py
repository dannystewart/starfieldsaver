# ruff: noqa: T201

from __future__ import annotations

import json
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

logger = LocalLogger.setup_logger("starfield_quicksave")


@dataclass
class Config:
    """Configuration for the quicksave behavior."""

    save_directory: str
    process_name: str = "Starfield"
    update_interval: float = 10.0
    quicksave_save: bool = True
    quicksave_save_interval: float = 240.0
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
    handle = win32api.OpenProcess(
        win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
    )
    try:
        process_path = win32process.GetModuleFileNameEx(handle, 0)
        return os.path.basename(process_path)
    finally:
        win32api.CloseHandle(handle)


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
        f"Save{new_save_id}_{datetime.now(tz=tz).strftime('%Y%m%d%H%M%S')}.sfs",
    )
    copy_file(source, destination)
    logger.info(
        "Copied quicksave %s to %s.",
        os.path.basename(source),
        os.path.basename(destination),
    )


def main() -> None:
    """Quicksave on interval."""
    config = load_config()
    keyboard = Controller()
    last_copy_time = None
    last_quicksave_time = None

    logger.info("Started quicksave utility for %s.", config.process_name)
    logger.debug("Configuration settings:")
    for key, value in asdict(config).items():
        logger.debug("  %s: %s", key, value)

    while True:
        try:
            time.sleep(config.update_interval)

            foreground_process = get_foreground_process_name()
            logger.debug("Current foreground process: %s", foreground_process)

            if not foreground_process.lower().startswith(config.process_name.lower()):
                logger.debug("Skipping because %s.exe was not in focus.", config.process_name)
                continue

            logger.debug("%s.exe is in focus, checking quicksave status.", config.process_name)

            current_time = datetime.now(tz=tz)

            # Handle quicksave creation
            if config.quicksave_save and (
                last_quicksave_time is None
                or (current_time - last_quicksave_time)
                >= timedelta(seconds=config.quicksave_save_interval)
            ):
                logger.info("Creating new quicksave.")
                keyboard.press(Key.f5)
                time.sleep(0.2)
                keyboard.release(Key.f5)
                last_quicksave_time = current_time

            # Find the latest quicksave file
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

        except KeyboardInterrupt:
            logger.info("Exiting quicksave utility.")
            break
        except Exception as e:
            logger.error("An error occurred: %s", str(e))


if __name__ == "__main__":
    main()

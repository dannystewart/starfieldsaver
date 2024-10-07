# ruff: noqa: T201

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import win32gui  # type: ignore
import win32process  # type: ignore
from dsutil.log import LocalLogger
from pynput.keyboard import Controller, Key

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


def main() -> None:
    """Quicksave on interval."""
    config = load_config()
    keyboard = Controller()

    while True:
        try:
            time.sleep(config.update_interval)

            if get_foreground_process_name() != config.process_name:
                logger.debug("Skipping because %s was not in focus.", config.process_name)
                continue

            # Simulate F5 key press to quicksave
            if config.quicksave_save:
                keyboard.press(Key.f5)
                time.sleep(0.2)
                keyboard.release(Key.f5)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
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


@dataclass
class QuicksaveConfig:
    """
    Configuration for behavior of the quicksave utility.

    Attributes:
        save_directory: Directory where save files are stored
        process_name: Name of the game process to monitor (without extension)
        check_interval: Time between checks (in seconds)
        quicksave_save: Whether to create quicksaves
        quicksave_interval: Time between quicksaves (in seconds)
        quicksave_copy: Whether to copy quicksaves to regular saves
    """

    save_directory: str
    process_name: str = "Starfield"
    check_interval: float = 10.0
    quicksave_save: bool = True
    quicksave_interval: float = 240.0
    quicksave_copy: bool = True


class QuicksaveUtility:
    """Quicksave utility for Starfield."""

    def __init__(self, debug: bool = False):
        self.logger = LocalLogger.setup_logger("quicksave", level="debug" if debug else "info")
        self.config = self.load_config()
        self.keyboard = Controller()
        self.last_copy_time: datetime | None = None
        self.last_quicksave_time: datetime | None = None

    def run(self) -> None:
        """Run the quicksave utility."""
        self.logger.info("Started quicksave utility for %s.", self.config.process_name)
        while True:
            try:
                time.sleep(self.config.check_interval)

                if not self.is_target_process_active():
                    continue

                if self.config.quicksave_save:
                    self.send_quicksave_key_to_game()

                if self.config.quicksave_copy:
                    self.copy_quicksave_to_regular_save()

            except KeyboardInterrupt:
                self.logger.info("Exiting quicksave utility.")
                break
            except Exception as e:
                self.logger.error("An error occurred: %s", str(e))

    def load_config(self) -> QuicksaveConfig:
        """Load the configuration from a JSON file or create a new one."""
        config_path = "quicksave.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = QuicksaveConfig(**json.load(f))
        else:
            quicksave_folder = os.path.join(
                os.path.expanduser("~"), "Documents", "My Games", "Starfield", "Saves"
            )
            config = QuicksaveConfig(quicksave_folder)
            with open(config_path, "w") as f:
                json.dump(config.__dict__, f, indent=2)

        self.logger.debug("Configuration loaded with settings:")
        for key, value in asdict(config).items():
            self.logger.debug("  %s: %s", key, value)

        return config

    def get_foreground_process_name(self) -> str:
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

    def is_target_process_active(self) -> bool:
        """Check if the target process is in focus."""
        foreground_process = self.get_foreground_process_name()
        self.logger.debug("Current foreground process: %s", foreground_process)
        if not foreground_process.lower().startswith(self.config.process_name.lower()):
            self.logger.debug("Skipping because %s.exe was not in focus.", self.config.process_name)
            return False
        self.logger.debug(
            "%s.exe is in focus, checking quicksave status.", self.config.process_name
        )
        return True

    def send_quicksave_key_to_game(self) -> None:
        """Create a new quicksave by sending F5 to the game."""
        current_time = datetime.now(tz=tz)
        if self.last_quicksave_time is None or (
            current_time - self.last_quicksave_time
        ) >= timedelta(seconds=self.config.quicksave_interval):
            self.logger.info("Creating new quicksave.")
            self.keyboard.press(Key.f5)
            time.sleep(0.2)
            self.keyboard.release(Key.f5)
            self.last_quicksave_time = current_time

    def copy_quicksave_to_regular_save(self) -> None:
        """Copy the latest quicksave to a regular save if newer than the last copied quicksave."""
        latest_quicksave = self.find_latest_quicksave_file()
        if latest_quicksave is None:
            self.logger.warning("No quicksave files found.")
            return

        quicksave_file, quicksave_time = latest_quicksave
        if self.last_copy_time is None or quicksave_time > self.last_copy_time:
            self.perform_quicksave_copy(quicksave_file)
            self.last_copy_time = quicksave_time

    def find_latest_quicksave_file(self) -> tuple[str, datetime] | None:
        """Find the latest quicksave file."""
        quicksaves = list_files(
            self.config.save_directory,
            extensions=["sfs"],
            sort_key=lambda x: x.stat().st_mtime,
            reverse_sort=True,
        )
        for quicksave in quicksaves:
            if os.path.basename(quicksave).startswith("Quicksave0"):
                return str(quicksave), datetime.fromtimestamp(os.path.getmtime(quicksave), tz=tz)
        return None

    def perform_quicksave_copy(self, source: str) -> None:
        """Copy the quicksave to a new file."""
        save_files = list_files(self.config.save_directory, extensions=["sfs"])
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
            self.config.save_directory,
            f"Save{new_save_id}_{datetime.now(tz=tz).strftime('%Y%m%d%H%M%S')}.sfs",
        )
        copy_file(source, destination)
        self.logger.info(
            "Copied quicksave %s to %s.",
            os.path.basename(source),
            os.path.basename(destination),
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Starfield Quicksave Utility")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    quicksave_utility = QuicksaveUtility(args.debug)
    quicksave_utility.run()

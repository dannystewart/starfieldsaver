from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import psutil
import win32api  # type: ignore
import win32con  # type: ignore
import win32file  # type: ignore
import win32gui  # type: ignore
import win32process  # type: ignore
from pynput.keyboard import Controller, Key
from watchdog.events import FileModifiedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer
from zoneinfo import ZoneInfo

from dsutil.files import list_files
from dsutil.log import LocalLogger

tz = ZoneInfo("America/New_York")

CONFIG_FILE_NAME = "quicksave.json"


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


class ConfigFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the quicksave configuration file."""

    def __init__(self, quicksave_utility: QuicksaveUtility):
        self.quicksave_utility = quicksave_utility

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Reload the configuration when the file is modified."""
        if not event.is_directory and event.src_path.endswith(CONFIG_FILE_NAME):
            self.quicksave_utility.reload_config()


class SaveFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the save directory."""

    def __init__(self, quicksave_utility: QuicksaveUtility):
        self.quicksave_utility = quicksave_utility

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle a file move in the save directory."""
        if (
            not event.is_directory
            and event.dest_path.endswith(".sfs")
            and "Quicksave0" in event.dest_path
        ):
            self.quicksave_utility.manual_quicksave_detected(event.dest_path)


class QuicksaveUtility:
    """Quicksave utility for Starfield."""

    def __init__(self, debug: bool = False):
        self.logger = LocalLogger.setup_logger("quicksave", level="debug" if debug else "info")
        self.config = self.load_config()
        self.keyboard = Controller()
        self.last_copy_time: datetime | None = None
        self.last_quicksave_time: datetime | None = None
        self.is_auto_saving = False
        self.setup_config_watcher()
        self.setup_save_watcher()

    def run(self) -> None:
        """Run the quicksave utility."""
        self.logger.info("Started quicksave utility for %s.exe.", self.config.process_name)

        try:
            while True:
                try:
                    time.sleep(self.config.check_interval)

                    if not self.is_target_process_running():
                        self.logger.debug(
                            "Skipped check because %s.exe is not running.", self.config.process_name
                        )
                        continue

                    if not self.is_target_process_active():
                        continue

                    if self.config.quicksave_save:
                        self.send_quicksave_key_to_game()

                    if self.config.quicksave_copy:
                        self.copy_quicksave_to_regular_save()

                except Exception as e:
                    self.logger.error("An error occurred during the main loop: %s", str(e))
                    time.sleep(2)  # Prevent rapid error loop

        except KeyboardInterrupt:
            self.logger.info("Exiting quicksave utility.")
        except Exception as e:
            self.logger.error("An error occurred: %s", str(e))
        finally:
            self.config_observer.stop()
            self.config_observer.join()
            self.save_observer.stop()
            self.save_observer.join()

    def load_config(self) -> QuicksaveConfig:
        """Load the configuration from a JSON file or create a new one."""
        max_retries = 3
        retry_delay = 0.1  # 100 ms

        for attempt in range(max_retries):
            try:
                if os.path.exists(CONFIG_FILE_NAME):
                    with open(CONFIG_FILE_NAME) as f:
                        config_data = json.load(f)
                    config = QuicksaveConfig(**config_data)
                else:
                    quicksave_folder = os.path.join(
                        os.path.expanduser("~"), "Documents", "My Games", "Starfield", "Saves"
                    )
                    config = QuicksaveConfig(quicksave_folder)
                    with open(CONFIG_FILE_NAME, "w") as f:
                        json.dump(config.__dict__, f, indent=2)

                self.logger.debug(
                    "Loaded config: check every %ss, %s%s",
                    round(config.check_interval),
                    f"save every {round(config.quicksave_interval)}s"
                    if config.quicksave_save
                    else "save disabled",
                    "" if config.quicksave_copy else ", copy disabled",
                )

                return config

            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(
                        "Error loading config (attempt %s): %s. Retrying...", attempt + 1, str(e)
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        "Failed to load config after %s attempts: %s", max_retries, str(e)
                    )
                    raise

    def reload_config(self) -> None:
        """Reload the configuration from the JSON file."""
        try:
            new_config = self.load_config()
            self.config = new_config
            self.logger.info("Reloaded config due to modification on disk.")
        except Exception as e:
            self.logger.warning(
                "Failed to reload config: %s. Continuing with previous config.", str(e)
            )

    def setup_config_watcher(self) -> None:
        """Watch for changes to the configuration file."""
        self.config_observer = Observer()
        handler = ConfigFileHandler(self)
        self.config_observer.schedule(handler, path=".", recursive=False)
        self.config_observer.start()

    def setup_save_watcher(self) -> None:
        """Watch for changes in the save directory."""
        self.save_observer = Observer()
        handler = SaveFileHandler(self)
        self.save_observer.schedule(handler, path=self.config.save_directory, recursive=False)
        self.save_observer.start()

    def is_target_process_running(self) -> bool:
        """Check if the target process (Starfield.exe) is running."""
        target_process = f"{self.config.process_name}.exe"
        return any(
            process.info["name"].lower() == target_process.lower()
            for process in psutil.process_iter(["name"])
        )

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
        if not foreground_process.lower().startswith(self.config.process_name.lower()):
            self.logger.debug("Skipped check because %s was in focus.", foreground_process)
            return False
        return True

    def send_quicksave_key_to_game(self) -> None:
        """Create a new quicksave by sending F5 to the game."""
        current_time = datetime.now(tz=tz)
        if self.last_quicksave_time is None or (
            current_time - self.last_quicksave_time
        ) >= timedelta(seconds=self.config.quicksave_interval):
            self.logger.info("Interval reached. Saving new quicksave.")
            self.is_auto_saving = True
            self.keyboard.press(Key.f5)
            time.sleep(0.2)
            self.keyboard.release(Key.f5)
            self.last_quicksave_time = current_time

    def copy_quicksave_to_regular_save(self) -> None:
        """Copy the latest quicksave to a regular save if newer than the last copied quicksave."""
        try:
            latest_quicksave = self.find_latest_quicksave_file()
            if latest_quicksave is None:
                self.logger.warning("No quicksave files found.")
                return

            quicksave_file, quicksave_time = latest_quicksave
            if not os.path.exists(quicksave_file):
                self.logger.warning("Quicksave file no longer exists: %s", quicksave_file)
                return

            if self.last_copy_time is None or quicksave_time > self.last_copy_time:
                self.perform_quicksave_copy(quicksave_file)
                self.last_copy_time = quicksave_time
        except FileNotFoundError as e:
            self.logger.warning("File not found during copy operation: %s", str(e))
        except Exception as e:
            self.logger.error("Error during copy operation: %s", str(e))

    def find_latest_quicksave_file(self) -> tuple[str, datetime] | None:
        """Find the latest quicksave file."""
        try:
            quicksaves = list_files(
                self.config.save_directory,
                extensions=["sfs"],
                sort_key=lambda x: x.stat().st_mtime,
                reverse_sort=True,
            )
            for quicksave in quicksaves:
                if os.path.basename(quicksave).startswith("Quicksave0"):
                    quicksave_path = str(quicksave)
                    if os.path.exists(quicksave_path):
                        return quicksave_path, datetime.fromtimestamp(
                            os.path.getmtime(quicksave_path), tz=tz
                        )
            return None
        except Exception as e:
            self.logger.error("Error finding latest quicksave: %s", str(e))
            return None

    def manual_quicksave_detected(self, quicksave_path: str) -> None:
        """Handle a manual quicksave event."""
        if self.is_auto_saving:
            self.is_auto_saving = False
            return

        quicksave_time = datetime.now(tz=tz)
        if self.last_quicksave_time is None or quicksave_time > self.last_quicksave_time:
            self.logger.info(
                "Resetting timer due to manual quicksave: %s", os.path.basename(quicksave_path)
            )
            self.last_quicksave_time = quicksave_time

    def copy_win32_file(self, source: str, destination: str) -> None:
        """Copy a file from source to destination, preserving attributes and permissions."""
        try:
            # Copy the file with metadata
            shutil.copy2(source, destination)

            # Ensure the destination file is not read-only
            os.chmod(destination, os.stat(source).st_mode)

            # Set file attributes to match the source
            source_attributes = win32file.GetFileAttributes(source)
            win32file.SetFileAttributes(destination, source_attributes)

            # Ensure the file is closed and not locked
            with open(destination, "a"):
                pass

        except Exception as e:
            msg = f"Failed to copy {source} to {destination}: {str(e)}"
            raise OSError(msg) from e

    def perform_quicksave_copy(self, source: str) -> bool:
        """Copy the quicksave to a new file with a name matching the game's format."""
        save_files = list_files(self.config.save_directory, extensions=["sfs"])
        source_filename = os.path.basename(source)

        # Find the highest save ID
        highest_save_id = max(
            [
                int(re.match(r"Save(\d+)_.*\.sfs", os.path.basename(f))[1])
                for f in save_files
                if re.match(r"Save\d+_.*\.sfs", os.path.basename(f))
            ]
            + [0]
        )
        new_save_id = highest_save_id + 1

        # Create the new save filename by replacing only the "Quicksave0" part
        new_filename = re.sub(r"^Quicksave0", f"Save{new_save_id}", source_filename)
        destination = os.path.join(self.config.save_directory, new_filename)

        try:
            self.copy_win32_file(source, destination)
            self.logger.debug("Copied previous quicksave to %s.", os.path.basename(destination))
            return True
        except Exception as e:
            self.logger.error("Failed to copy file: %s", str(e))
            return False


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Starfield Quicksave Utility")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    quicksave_utility = QuicksaveUtility(args.debug)
    quicksave_utility.run()

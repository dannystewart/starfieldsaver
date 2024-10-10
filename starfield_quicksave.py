from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import psutil
import win32api  # type: ignore
import win32con  # type: ignore
import win32gui  # type: ignore
import win32process  # type: ignore
from pynput.keyboard import Controller, Key
from watchdog.observers import Observer

from config_loader import ConfigLoader
from dsutil.files import copy_win32_file, list_files
from dsutil.log import LocalLogger
from file_watchers import ConfigFileHandler, SaveFileHandler
from globals import TZ
from sound_player import SoundPlayer

if TYPE_CHECKING:
    import logging


class QuicksaveUtility:
    """Quicksave utility for Starfield."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.logger = self._setup_logger()

        # Initialize keyboard and sound player
        self.keyboard = Controller()
        self.sound = SoundPlayer(self.logger)

        # Initialize last save times and flags
        self.last_copy_time: datetime | None = None
        self.last_quicksave_time: datetime | None = None
        self.save_in_progress = False

        # Set up file watchers and log configuration
        self._setup_config_watcher()
        self._setup_save_watcher()
        self._log_config()

    def run(self) -> None:
        """Run the quicksave utility."""
        self.logger.info("Started quicksave utility for %s.exe.", self.config.process_name)

        try:
            while True:
                try:
                    time.sleep(self.config.check_interval)

                    if not self.is_target_process_running():
                        self.logger.debug(
                            "Skipping check because %s.exe is not running.",
                            self.config.process_name,
                        )
                        continue

                    if not self.is_target_process_active():
                        continue

                    if self.config.quicksave_save:
                        self.send_quicksave_key_to_game()

                    if self.config.quicksave_copy:
                        self.copy_to_regular_save()

                except Exception as e:
                    self.logger.error("An error occurred during the main loop: %s", str(e))
                    self.sound.play_error()
                    time.sleep(2)  # Prevent rapid error loop

        except KeyboardInterrupt:
            self.logger.info("Exiting quicksave utility.")
        except Exception as e:
            self.logger.error("An error occurred: %s", str(e))
            self.sound.play_error()
        finally:
            self.config_observer.stop()
            self.config_observer.join()
            self.save_observer.stop()
            self.save_observer.join()

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
            self.logger.debug("Skipping check because %s is in focus.", foreground_process)
            return False
        return True

    def send_quicksave_key_to_game(self) -> None:
        """Create a new quicksave by sending F5 to the game."""
        current_time = datetime.now(tz=TZ)
        if self.last_quicksave_time is None or (
            current_time - self.last_quicksave_time
        ) >= timedelta(seconds=self.config.quicksave_interval):
            self.logger.info("Scheduled interval time reached; sending quicksave key to game.")
            self.save_in_progress = True
            self.keyboard.press(Key.f5)
            time.sleep(0.2)
            self.keyboard.release(Key.f5)
            self.last_quicksave_time = current_time

    def copy_to_regular_save(self) -> None:
        """Copy the latest quicksave to a regular save if newer than the last copied quicksave."""
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                if result := self._attempt_save_copy():
                    return
                if result is False:  # No new quicksave to copy
                    return

            # If result is None, it means we should retry
            except Exception as e:
                self.logger.error(
                    "Error during copy operation (attempt %d): %s", attempt + 1, str(e)
                )

            if attempt < max_attempts - 1:
                self.logger.info("Retrying copy operation...")
                time.sleep(1)  # Wait a second before retrying
            else:
                self.sound.play_error()  # Play error sound after all attempts fail
                self.logger.error("Failed to copy quicksave after %d attempts", max_attempts)

    def _attempt_save_copy(self) -> bool | None:
        """
        Attempt to copy the latest quicksave file.

        Returns:
            - True if the copy was successful.
            - False if no copy was needed.
            - None to indicate the save should be retried.
        """
        latest_quicksave = self.find_latest_quicksave()
        if latest_quicksave is None:
            self.logger.warning("No quicksave files found.")
            return None  # Should retry

        quicksave_file, quicksave_time = latest_quicksave
        if not os.path.exists(quicksave_file):
            self.logger.warning("Quicksave file no longer exists: %s", quicksave_file)
            return None  # Should retry

        if self.last_copy_time is None or quicksave_time > self.last_copy_time:
            if self.copy_save(quicksave_file):
                self.last_copy_time = quicksave_time
                return True  # Copied successfully
            return None  # Should retry
        return False  # No copy needed

    def _get_new_save_id(self, save_files: list[str]) -> int:
        """Get the next available save ID."""
        highest_save_id = max(
            [
                int(re.match(r"Save(\d+)_.*\.sfs", os.path.basename(f))[1])
                for f in save_files
                if re.match(r"Save\d+_.*\.sfs", os.path.basename(f))
            ]
            + [0]
        )
        return highest_save_id + 1

    def find_latest_quicksave(self) -> tuple[str, datetime] | None:
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
                            os.path.getmtime(quicksave_path), tz=TZ
                        )
            return None
        except Exception as e:
            self.logger.error("Error finding latest quicksave: %s", str(e))
            return None

    def manual_quicksave_detected(self, quicksave_path: str) -> None:
        """Handle a manual quicksave event."""
        if self.save_in_progress:
            self.save_in_progress = False
            return

        quicksave_time = datetime.now(tz=TZ)
        if self.last_quicksave_time is None or quicksave_time > self.last_quicksave_time:
            self.logger.info(
                "Resetting timer due to manual quicksave: %s", os.path.basename(quicksave_path)
            )
            self.last_quicksave_time = quicksave_time
            self.sound.play_info()

    def copy_save(self, source: str) -> bool:
        """Copy the save to a new file with a name matching the game's format."""
        save_files = list_files(self.config.save_directory, extensions=["sfs"])
        source_filename = os.path.basename(source)

        new_save_id = self._get_new_save_id(save_files)
        new_filename = re.sub(r"^Quicksave0", f"Save{new_save_id}", source_filename)
        destination = os.path.join(self.config.save_directory, new_filename)

        try:
            copy_win32_file(source, destination)
            self.sound.play_success()
            save_type = self.identify_save_type(new_filename)
            self.logger.info("Copied %s to %s.", save_type, os.path.basename(destination))
            return True
        except Exception as e:
            self.logger.error("Failed to copy file: %s", str(e))
            return False

    def reload_config(self) -> None:
        """Reload the configuration from the JSON file."""
        self.config = ConfigLoader.reload(self.config, self.logger)
        self._log_config()

    def _setup_logger(self) -> logging.Logger:
        log_level = "debug" if self.config.debug_log else "info"
        return LocalLogger.setup_logger("quicksave", level=log_level)

    def _setup_config_watcher(self) -> None:
        self.config_observer = Observer()
        handler = ConfigFileHandler(self)
        self.config_observer.schedule(handler, path=".", recursive=False)
        self.config_observer.start()

    def _setup_save_watcher(self) -> None:
        self.save_observer = Observer()
        handler = SaveFileHandler(self)
        self.save_observer.schedule(handler, path=self.config.save_directory, recursive=False)
        self.save_observer.start()

    def _log_config(self) -> None:
        self.logger.debug(
            "Loaded config: check every %ss, %s%s, sounds %s",
            round(self.config.check_interval),
            f"save every {round(self.config.quicksave_interval)}s"
            if self.config.quicksave_save
            else "save disabled",
            "" if self.config.quicksave_copy else ", copy disabled",
            "enabled" if self.config.enable_sounds else "disabled",
        )


if __name__ == "__main__":
    QuicksaveUtility().run()

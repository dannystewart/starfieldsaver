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
        self.keyboard = Controller()
        self.sound = SoundPlayer(self.logger)

        self.last_quicksave_time: datetime | None = None
        self.last_copied_save_name: str | None = None
        self.is_scheduled_save: bool = False

        self._setup_config_watcher()
        self._setup_save_watcher()
        self._log_config()

    def run(self) -> None:
        """Run the quicksave utility."""
        self.logger.info("Started quicksave utility for %s.exe.", self.config.process_name)

        try:
            self._main_loop()
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

    def _main_loop(self) -> None:
        while True:
            try:
                time.sleep(self.config.check_interval)

                if not self._is_target_process_running():
                    self.logger.debug(
                        "Skipping check because %s.exe is not running.", self.config.process_name
                    )
                    continue

                if not self._is_target_process_active():
                    continue

                if self.config.quicksave_save:
                    self.save_on_interval()

            except Exception as e:
                self.logger.error("An error occurred during the main loop: %s", str(e))
                self.sound.play_error()
                time.sleep(2)  # Prevent rapid error loop

    def _is_target_process_running(self) -> bool:
        target_process = f"{self.config.process_name}.exe"
        return any(
            process.info["name"].lower() == target_process.lower()
            for process in psutil.process_iter(["name"])
        )

    def _is_target_process_active(self) -> bool:
        foreground_process = self._get_foreground_process_name()
        if not foreground_process.lower().startswith(self.config.process_name.lower()):
            self.logger.debug("Skipping check because %s is in focus.", foreground_process)
            return False
        return True

    def _get_foreground_process_name(self) -> str:
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

    def save_on_interval(self) -> None:
        """Create a new quicksave by sending F5 to the game."""
        current_time = datetime.now(tz=TZ)
        if self.last_quicksave_time is None or (
            current_time - self.last_quicksave_time
        ) >= timedelta(seconds=self.config.quicksave_interval):
            self.logger.info("Scheduled interval reached; sending quicksave command to game.")
            self.is_scheduled_save = True
            self.keyboard.press(Key.f5)
            time.sleep(0.2)
            self.keyboard.release(Key.f5)
            self.last_quicksave_time = current_time

    def new_game_save_detected(self, save_path: str) -> None:
        """Handle a manual quicksave event or an autosave event."""
        self.logger.info("New save file detected: %s", os.path.basename(save_path))

        # If this was a scheduled interval save, treat it as automatic
        if self.is_scheduled_save:
            self.logger.debug("Quicksave was scheduled. Copying to regular save.")
            self.copy_save_to_new_file(save_path, auto=True)
            self.is_scheduled_save = False
            return

        save_time = datetime.fromtimestamp(os.path.getmtime(save_path), tz=TZ)

        if self.last_quicksave_time is None or save_time > self.last_quicksave_time:
            save_type = "autosave" if "Autosave" in save_path else "quicksave"
            if save_type == "quicksave":
                self.logger.info(
                    "Resetting timer due to user-initiated quicksave: %s",
                    os.path.basename(save_path),
                )
                self.last_quicksave_time = save_time
                self.copy_save_to_new_file(save_path, auto=False)
            else:
                self.logger.info("New autosave detected: %s", os.path.basename(save_path))
                self.copy_save_to_new_file(save_path, auto=True)

    def copy_save_to_new_file(self, source: str, auto: bool) -> bool:
        """Copy the save to a new file with a name matching the game's format."""
        if source == self.last_copied_save_name:
            self.logger.debug("Skipping save already copied: %s", os.path.basename(source))
            return False

        save_files = list_files(self.config.save_directory, extensions=["sfs"])
        source_filename = os.path.basename(source)

        highest_save_id, next_save_id = self._get_next_save_id(save_files)
        self.logger.debug(
            "Found %s saves. Highest ID is %s. Next ID is %s.",
            len(save_files),
            highest_save_id,
            next_save_id,
        )

        new_filename = re.sub(r"^(Quicksave0|Autosave)", f"Save{next_save_id}", source_filename)
        destination = os.path.join(self.config.save_directory, new_filename)

        try:
            copy_win32_file(source, destination)
            self.logger.info(
                "Copied most recent %s to %s.",
                self._identify_save_type(source),
                os.path.basename(destination),
            )
            if auto:
                self.sound.play_success()
            else:
                self.sound.play_notification()
            self.last_copied_save_name = source
            return True
        except Exception as e:
            self.logger.error("Failed to copy file: %s", str(e))
            self.sound.play_error()
            return False

    def _get_next_save_id(self, save_files: list[str]) -> tuple[int, int]:
        """Get the next available save ID. Returns highest existing and next IDs."""
        save_ids = []
        for f in save_files:
            if match := re.match(r"Save(\d{1,4})_[A-F0-9]{8}", os.path.basename(f)):
                try:
                    save_id = int(match[1])
                    save_ids.append(save_id)
                except ValueError:
                    self.logger.error("Failed to parse save ID for file: %s", f)

        if not save_ids:
            self.logger.warning("No valid save IDs found, starting from 0")
            return 1

        highest_save_id = max(save_ids)
        next_save_id = highest_save_id + 1
        return highest_save_id, next_save_id

    def _identify_save_type(self, save_path: str) -> str:
        return (
            "quicksave"
            if "Quicksave0" in save_path
            else "autosave"
            if "Autosave" in save_path
            else "manual save"
        )

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

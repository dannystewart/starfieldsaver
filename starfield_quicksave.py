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

from config_loader import ConfigLoader, SaveType
from dsutil.files import copy_win32_file, list_files
from dsutil.log import LocalLogger
from file_watchers import ConfigFileHandler, SaveFileHandler
from globals import TZ
from sound_player import SoundPlayer

if TYPE_CHECKING:
    import logging

    from config_loader import QuicksaveConfig


class QuicksaveUtility:
    """Quicksave utility for Starfield."""

    def __init__(self):
        self.config: QuicksaveConfig = ConfigLoader.load()
        self.logger = self._setup_logger()
        self.keyboard = Controller()
        self.sound = SoundPlayer(self.logger)

        # Variables to track save information
        self.last_quicksave_time: datetime | None = None
        self.last_copied_save_name: str | None = None
        self.is_scheduled_save: bool = False

        # Variables to track process information
        self.game_is_running: bool = True
        self.game_in_foreground: bool = True
        self.last_foreground_process: str = ""

        # Variables to track logging
        self.logging_paused = False
        self.last_logging_check = datetime.now(tz=TZ)

        # How often to log reminder that checks are still on hold
        self.reminder_default = timedelta(seconds=600)  # 10 minutes
        self.reminder_interval = self.reminder_default

        # How much to increment the reminder time by each time
        self.reminder_increment = timedelta(seconds=300)  # 5 minutes

        # Maximum time in minutes before the reminder stops incrementing
        self.reminder_max_minutes = 30

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
                self._check_logging_status()

                if not self._is_game_running():
                    continue

                if not self._is_game_in_foreground():
                    continue

                if self.config.quicksave_save:
                    self.save_on_interval()

            except Exception as e:
                self.logger.error("An error occurred during the main loop: %s", str(e))
                self.sound.play_error()
                time.sleep(2)  # Prevent rapid error loop

    def save_on_interval(self) -> None:
        """Create a new quicksave by sending F5 to the game."""
        current_time = datetime.now(tz=TZ)
        if self.last_quicksave_time is None or (
            current_time - self.last_quicksave_time
        ) >= timedelta(seconds=self.config.quicksave_interval):
            self.is_scheduled_save = True
            self.keyboard.press(Key.f5)
            time.sleep(0.2)
            self.keyboard.release(Key.f5)
            self.logger.info("Created quicksave at scheduled interval time.")
            self.last_quicksave_time = current_time

    @staticmethod
    def identify_save_type(save_path: str) -> SaveType:
        """Identify the type of save based on the file name."""
        if "Quicksave0" in save_path:
            return SaveType.QUICKSAVE
        return SaveType.AUTOSAVE if "Autosave" in save_path else SaveType.MANUAL

    def new_game_save_detected(self, save_path: str) -> None:
        """Handle a manual quicksave event or an autosave event."""
        self.logger.debug("New save detected: %s", os.path.basename(save_path))
        save_type = self.identify_save_type(save_path)

        if save_type == SaveType.MANUAL:
            self.logger.debug("Skipping manual save: %s", os.path.basename(save_path))
            return

        # If this was a scheduled interval save, treat it as automatic
        if self.is_scheduled_save:
            self.logger.info(
                "Copying new scheduled quicksave to regular save: %s", os.path.basename(save_path)
            )
            self.copy_save_to_new_file(save_path, auto=True, scheduled=True)
            self.is_scheduled_save = False
            return

        save_time = datetime.fromtimestamp(os.path.getmtime(save_path), tz=TZ)

        if self.last_quicksave_time is None or save_time > self.last_quicksave_time:
            if save_type == SaveType.QUICKSAVE:
                self.logger.info(
                    "Resetting interval timer due to user-initiated quicksave: %s",
                    os.path.basename(save_path),
                )
                self.last_quicksave_time = save_time
                self.copy_save_to_new_file(save_path, auto=False)
            elif save_type == SaveType.AUTOSAVE:
                self.logger.info("New autosave detected: %s", os.path.basename(save_path))
                self.copy_save_to_new_file(save_path, auto=True)

    def copy_save_to_new_file(self, source: str, auto: bool, scheduled: bool = False) -> bool:
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
                "Copied most recent %s%s to %s.",
                "scheduled " if scheduled else "",
                self.identify_save_type(source),
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
            return 0, 1

        highest_save_id = max(save_ids)

        # Determine the number of digits in the highest save ID
        digit_count = len(str(highest_save_id))

        # Calculate the maximum possible ID for the current digit count
        max_id_for_digits = 10**digit_count - 1

        # If we've reached the maximum for the current digit count, start over
        if highest_save_id == max_id_for_digits:
            next_save_id = 10 ** (digit_count - 1)
        else:
            next_save_id = highest_save_id + 1

        return highest_save_id, next_save_id

    def _is_game_running(self) -> bool:
        game_process = f"{self.config.process_name}.exe"
        is_running = any(
            process.info["name"].lower() == game_process.lower()
            for process in psutil.process_iter(["name"])
        )

        if not is_running:
            if self.game_is_running:
                self.logger.info(
                    "Skipping checks while %s.exe is not running.",
                    self.config.process_name,
                )
            self.game_is_running = False
        else:
            self.game_is_running = True

        return is_running

    def _is_game_in_foreground(self) -> bool:
        foreground_process = self._get_foreground_process()
        is_active = foreground_process.lower().startswith(self.config.process_name.lower())

        if not is_active:
            if self.game_in_foreground or foreground_process != self.last_foreground_process:
                self.logger.info("Skipping checks while %s is in focus.", foreground_process)
            self.game_in_foreground = False
            self.last_foreground_process = foreground_process
        else:
            self.game_in_foreground = True

        return is_active

    def _get_foreground_process(self) -> str:
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

    def reload_config(self) -> None:
        """Reload the configuration from the JSON file."""
        self.config = ConfigLoader.reload(self.config, self.logger)
        self._log_config()

    def _setup_logger(self) -> logging.Logger:
        level = "debug" if self.config.debug_log else "info"
        color = self.config.color_log
        return LocalLogger.setup_logger("quicksave", level=level, use_color=color)

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

    def _check_logging_status(self) -> None:
        current_time = datetime.now(tz=TZ)
        if self.game_is_running and self.game_in_foreground:
            self.logging_paused = False
            self.reminder_interval = self.reminder_default

        elif not self.logging_paused:
            self.logging_paused = True
            self.last_logging_check = current_time
            self._increment_reminder_time()

        elif current_time - self.last_logging_check > self.reminder_interval:
            self.logger.info("Still waiting for %s.exe.", self.config.process_name)
            self.last_logging_check = current_time
            self._increment_reminder_time()

    def _format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    def _increment_reminder_time(self) -> None:
        if self.reminder_interval < timedelta(minutes=self.reminder_max_minutes):
            self.reminder_interval += self.reminder_increment
            formatted_time = self._format_timedelta(self.reminder_interval)
            self.logger.debug("Reminder interval increased to %s.", formatted_time)


if __name__ == "__main__":
    QuicksaveUtility().run()

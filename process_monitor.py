from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import psutil
from watchdog.observers import Observer

from config_loader import ConfigFileHandler, SaveFileHandler
from globals import TZ

if sys.platform == "win32":
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32gui  # type: ignore
    import win32process  # type: ignore

if TYPE_CHECKING:
    from quicksave_utility import QuicksaveUtility


class ProcessMonitor:
    """Process monitor for Starfield quicksave utility."""

    def __init__(self, quicksave_utility: QuicksaveUtility):
        self.saver: QuicksaveUtility = quicksave_utility
        self.logger = quicksave_utility.logger

        # Variables to track process information
        self.game_is_running: bool = True
        self.game_in_foreground: bool = True
        self.last_foreground_process: str = ""

        # Variables to track logging
        self.logging_paused = False
        self.last_logging_check = datetime.now(tz=TZ)

        # How often to log reminder that checks are still on hold
        self.reminder_default = timedelta(seconds=60)  # 1 minute
        self.reminder_interval = self.reminder_default

        # How much to increment the reminder time by each time
        self.reminder_increment = timedelta(seconds=60)  # 1 minute

        # Maximum time in minutes before the reminder stops incrementing
        self.reminder_max_minutes = 30

        self.setup_config_watcher()
        self.setup_save_watcher()

    def is_game_running(self) -> bool:
        """Check if the game process is running."""
        game_process = f"{self.saver.config.process_name}.exe"
        is_running = any(
            process.info["name"].lower() == game_process.lower()
            for process in psutil.process_iter(["name"])
        )

        if not is_running:
            if self.game_is_running:
                self.logger.info(
                    "Skipping checks while %s.exe is not running.",
                    self.saver.config.process_name,
                )
            self.game_is_running = False
        else:
            self.game_is_running = True

        return is_running

    def is_game_in_foreground(self) -> bool:
        """Check if the game is in running in the foreground."""
        foreground_process = self.get_foreground_process()
        is_active = foreground_process.lower().startswith(self.saver.config.process_name.lower())

        if not is_active:
            if self.game_in_foreground or foreground_process != self.last_foreground_process:
                self.logger.info("Skipping checks while %s is in focus.", foreground_process)
            self.game_in_foreground = False
            self.last_foreground_process = foreground_process
        else:
            self.game_in_foreground = True

        return is_active

    def get_foreground_process(self) -> str:
        """Get the name of the process currently in the foreground."""
        if sys.platform != "win32":
            return ""

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

    def setup_config_watcher(self) -> None:
        """Set up a file watcher to monitor the config file."""
        self.config_observer = Observer()
        handler = ConfigFileHandler(self.saver)
        self.config_observer.schedule(handler, path=".", recursive=False)
        self.config_observer.start()

    def setup_save_watcher(self) -> None:
        """Set up a file watcher to monitor the save directory."""
        self.save_observer = Observer()
        handler = SaveFileHandler(self.saver)
        self.save_observer.schedule(handler, path=self.saver.config.save_directory, recursive=False)
        self.save_observer.start()

    def check_logging_status(self) -> None:
        """Check if logging should be paused or resumed."""
        current_time = datetime.now(tz=TZ)
        if self.game_is_running and self.game_in_foreground:
            self.logging_paused = False
            self.reminder_interval = self.reminder_default

        elif not self.logging_paused:
            self.logging_paused = True
            self.last_logging_check = current_time
            self._increment_reminder_time()

        elif current_time - self.last_logging_check > self.reminder_interval:
            self.logger.info("Still waiting for %s.exe.", self.saver.config.process_name)
            self.last_logging_check = current_time
            self._increment_reminder_time()

    def _format_timedelta(self, td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return (
            f"{minutes}m"
            if seconds == 0
            else f"{minutes}m {seconds}s"
            if minutes > 0
            else f"{seconds}s"
        )

    def _increment_reminder_time(self) -> None:
        if self.reminder_interval < timedelta(minutes=self.reminder_max_minutes):
            self.reminder_interval += self.reminder_increment
            formatted_time = self._format_timedelta(self.reminder_interval)
            self.logger.debug("Next inactivity reminder in %s.", formatted_time)

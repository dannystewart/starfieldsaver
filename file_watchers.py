from __future__ import annotations

import os
from typing import TYPE_CHECKING

from watchdog.events import FileModifiedEvent, FileMovedEvent, FileSystemEventHandler

from globals import CONFIG_FILE_NAME

if TYPE_CHECKING:
    from quicksave_utility import QuicksaveUtility


class ConfigFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the quicksave configuration file."""

    def __init__(self, quicksave_utility: QuicksaveUtility):
        self.saver = quicksave_utility

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Reload the configuration when the file is modified."""
        if not event.is_directory and event.src_path.endswith(CONFIG_FILE_NAME):
            self.saver.reload_config()


class SaveFileHandler(FileSystemEventHandler):
    """Watchdog event handler for changes to the save directory."""

    def __init__(self, quicksave_utility: QuicksaveUtility):
        self.saver = quicksave_utility

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle a file move in the save directory."""
        self.saver.logger.debug(
            "Move event detected: %s -> %s",
            os.path.basename(event.src_path),
            os.path.basename(event.dest_path),
        )

        if not event.is_directory and event.dest_path.endswith(".sfs"):
            if self.saver.config.quicksave_copy:
                self.saver.new_game_save_detected(event.dest_path)
        else:
            self.saver.logger.debug("Moved file is not a game save, ignoring.")

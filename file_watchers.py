from __future__ import annotations

import os
from typing import TYPE_CHECKING

from watchdog.events import FileModifiedEvent, FileMovedEvent, FileSystemEventHandler

from globals import CONFIG_FILE_NAME

if TYPE_CHECKING:
    from starfield_quicksave import QuicksaveUtility


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
            and event.src_path.endswith(".sfs")
            and ("Quicksave0" in event.src_path or "Autosave" in event.src_path)
        ):
            self.quicksave_utility.logger.debug(
                "New file detected: %s", os.path.basename(event.src_path)
            )
            if self.quicksave_utility.config.quicksave_copy:
                self.quicksave_utility.copy_save(event.src_path)

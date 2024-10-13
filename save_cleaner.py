from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from config_loader import QuicksaveConfig
from dsutil.files import delete_files, list_files
from globals import TZ

if TYPE_CHECKING:
    import logging
    from pathlib import Path

    from config_loader import QuicksaveConfig


class SaveCleaner:
    """Save cleanup for Starfield."""

    def __init__(self, config: QuicksaveConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

        self.cleanup_interval = timedelta(hours=24)  # Run cleanup once a day
        self.last_cleanup_time = datetime.now(tz=TZ)

    def cleanup_saves_if_scheduled(self) -> None:
        """Run save cleanup if it's time."""
        self.logger.debug("Checking if save cleanup is scheduled...")

        current_time = datetime.now(tz=TZ)
        if current_time - self.last_cleanup_time >= self.cleanup_interval:
            self.cleanup_old_saves()
            self.last_cleanup_time = current_time

    def cleanup_old_saves(self) -> None:
        """Clean up old saves, keeping one per day beyond the cutoff date."""
        if self.config.days_before_pruning_saves == 0:
            self.logger.info("Save cleanup disabled (days_before_pruning_saves is 0).")
            return

        self.logger.info("Starting save cleanup process...")

        save_files = list_files(
            self.config.save_directory,
            extensions=["sfs"],
            sort_key=lambda x: x.stat().st_mtime,
            reverse_sort=True,
        )

        if not save_files:
            self.logger.info("No save files found to clean up.")
            return

        self.logger.info("Total saves found: %s", len(save_files))

        most_recent_save_time = datetime.fromtimestamp(save_files[0].stat().st_mtime, tz=TZ)
        cutoff_date = most_recent_save_time - timedelta(days=self.config.days_before_pruning_saves)
        self.logger.info("Cutoff date for save deletion: %s", cutoff_date)

        # Group saves by character
        character_saves = defaultdict(list)
        for save_file in save_files:
            character_id, timestamp = self._parse_save_name(str(save_file))
            if character_id and timestamp:
                character_saves[character_id].append((save_file, timestamp))

        self.logger.info("Processed saves for %s characters.", len(character_saves))

        files_to_delete = []
        for character_id, saves in character_saves.items():
            self.logger.info("Processing saves for character: %s", character_id)
            files_to_delete.extend(self._get_files_to_delete(saves, cutoff_date))

        self.logger.info("Total saves to delete: %s", len(files_to_delete))
        self.logger.info("Total saves to keep: %s", len(save_files) - len(files_to_delete))

        successful, failed = delete_files(
            files_to_delete, show_output=False, dry_run=self.config.save_cleanup_dry_run
        )

        if self.config.save_cleanup_dry_run:
            self.logger.info(
                "Dry run: would delete %s old saves across all characters.", successful
            )
        else:
            self.logger.info(
                "Save cleanup complete. Kept %s saves, deleted %s saves, failed to delete %s saves.",
                len(save_files) - len(files_to_delete),
                successful,
                failed,
            )

        if failed > 0:
            self.logger.warning("Failed to delete %s saves.", failed)

    def _get_files_to_delete(
        self, saves: list[tuple[Path, datetime]], cutoff_date: datetime
    ) -> list[Path]:
        """Determine which saves should be deleted for a character."""
        saves_to_keep = set()
        saves_by_date = defaultdict(list)
        files_to_delete = []

        # Sort saves by timestamp (newest first)
        saves.sort(key=lambda x: x[1], reverse=True)

        for save_file, save_time in saves:
            save_time = save_time.replace(tzinfo=TZ)
            if save_time >= cutoff_date:
                saves_to_keep.add(save_file)
            else:
                save_date = save_time.date()
                saves_by_date[save_date].append(save_file)

        # For dates before cutoff, keep only the latest save
        for date, date_saves in saves_by_date.items():
            date_saves.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            saves_to_keep.add(date_saves[0])
            self.logger.info(
                "Preserving save from %s (before cutoff): %s", date, date_saves[0].name
            )

        for save_file, _ in saves:
            if save_file not in saves_to_keep:
                files_to_delete.append(save_file)
                self.logger.warning(
                    "%s old save: %s",
                    "Would delete" if self.config.save_cleanup_dry_run else "Deleting",
                    save_file.name,
                )

        return files_to_delete

    def _parse_save_name(self, save_path: str) -> tuple[str, datetime]:
        """Extract character ID and timestamp from save file name."""
        filename = os.path.basename(save_path)
        parts = filename.split("_")

        # Try to find the timestamp by looking for a part that starts with '202'
        timestamp_part = next((part for part in parts if part.startswith("202")), None)

        # If not found, try getting the 5th part from the end (assuming consistent format)
        if not timestamp_part and len(parts) >= 5:
            timestamp_part = parts[-5]

        if not timestamp_part:
            self.logger.warning("Could not parse timestamp from filename: %s", filename)
            return None, None

        try:
            timestamp = datetime.strptime(timestamp_part, "%Y%m%d%H%M%S")
        except ValueError:
            self.logger.warning("Invalid timestamp format in filename: %s", filename)
            return None, None

        # Character ID is the second part (index 1) in the filename
        character_id = parts[1] if len(parts) > 1 else None

        if not character_id:
            self.logger.warning("Could not parse character ID from filename: %s", filename)
            return None, None

        return character_id, timestamp

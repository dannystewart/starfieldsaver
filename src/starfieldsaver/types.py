from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar


class SaveType(StrEnum):
    """Save types for Starfield."""

    QUICKSAVE = "quicksave"
    AUTOSAVE = "autosave"
    MANUAL = "manual save"


@dataclass
class QuicksaveConfig:
    """Configuration for behavior of the quicksave utility.

    Attributes:
        save_dir: Directory where save files are stored.
        game_exe: Name of the game process to monitor.
        check_interval: Time between status checks (in seconds).
        quicksave_every: Time between quicksaves (in seconds).
        enable_quicksave: Whether to enable quicksaving on the set interval.
        copy_to_regular_save: Whether to copy quicksaves to regular saves.
        prune_older_than_days: Number of days before pruning saves to one per day (0 to keep all).
        dry_run: Whether to perform a dry run of save cleanup (log only).
        enable_success_sounds: Whether to play sounds on events.
        enable_debug: Whether to enable debug logging.
    """

    save_dir: str
    game_exe: str = "Starfield.exe"
    enable_quicksave: bool = True
    check_interval: float = 10
    quicksave_every: float = 240
    copy_to_regular_save: bool = True
    prune_older_than_days: int = 0
    dry_run: bool = True
    enable_success_sounds: bool = True
    enable_debug: bool = False
    extra_config: dict[str, Any] = field(default_factory=dict)

    # Define the structure of the TOML file
    config_structure: ClassVar[dict[str, list[str]]] = {
        "paths": ["save_dir", "game_exe"],
        "saves": [
            "enable_quicksave",
            "check_interval",
            "quicksave_every",
            "copy_to_regular_save",
            "enable_success_sounds",
        ],
        "cleanup": ["prune_older_than_days", "dry_run"],
        "logging": ["enable_debug"],
    }

    def __post_init__(self):
        # Append .exe to filename if not already present
        self.game_exe = (
            f"{self.game_exe}.exe" if not self.game_exe.endswith(".exe") else self.game_exe
        )

        # Get any additional config items not in the annotations
        self.extra_config = {
            k: v for k, v in self.__dict__.items() if k not in self.__annotations__
        }
        for k in self.extra_config:
            delattr(self, k)

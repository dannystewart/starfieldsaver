"""A utility to automatically quicksave in Starfield on a specified interval."""

from __future__ import annotations

from quicksave_utility import QuicksaveUtility
from version_updater import VersionUpdater

if __name__ == "__main__":
    VersionUpdater().check_for_updates()
    QuicksaveUtility().run()

"""A utility to automatically quicksave in Starfield on a specified interval."""

from __future__ import annotations

from dsutil.errors import configure_traceback
from dsutil.log import LocalLogger
from quicksave_utility import QuicksaveUtility
from version_updater import VersionUpdater

configure_traceback()

logger = LocalLogger.setup_logger()
updater = VersionUpdater()

if __name__ == "__main__":
    updater.cleanup_old_version()
    updater.check_for_updates()

    try:
        QuicksaveUtility().run()
    except Exception as e:
        logger.error("An error occurred while running the application: %s", str(e))

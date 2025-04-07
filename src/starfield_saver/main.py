"""A utility to automatically quicksave in Starfield on a specified interval."""

from __future__ import annotations

from polykit.core import polykit_setup
from polykit.log import PolyLog

from starfield_saver.quicksave_utility import QuicksaveUtility
from starfield_saver.version_updater import VersionUpdater

polykit_setup()

logger = PolyLog.get_logger("starfield_saver")
updater = VersionUpdater()


def main():
    """Main function to run the quicksave utility."""
    updater.cleanup_old_version()
    updater.check_for_updates()

    try:
        QuicksaveUtility().run()
    except Exception as e:
        logger.error("An error occurred while running the application: %s", str(e))


if __name__ == "__main__":
    main()

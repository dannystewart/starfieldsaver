"""A utility to automatically quicksave in Starfield on a specified interval."""

from __future__ import annotations

import sys

from polykit.core import platform_check, polykit_setup
from polykit.log import PolyLog

from starfieldsaver.quicksave_utility import QuicksaveUtility

polykit_setup()

if not platform_check("Windows"):
    sys.exit(1)

logger = PolyLog.get_logger("starfieldsaver")


def main():
    """Main function to run the quicksave utility."""
    try:
        QuicksaveUtility().run()
    except Exception as e:
        logger.error("An error occurred while running the application: %s", str(e))


if __name__ == "__main__":
    main()

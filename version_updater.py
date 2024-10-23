import json
import os
import subprocess
import sys

import requests

from dsutil.log import LocalLogger

CURRENT_VERSION = "1.5.1"
VERSION_URL = "https://gitlab.dannystewart.com/danny/starfield-saver/-/raw/main/version.json"


class VersionUpdater:
    """Check for updates and prompt the user to update if a new version is available."""

    def __init__(self):
        self.logger = LocalLogger.setup_logger()

    def check_for_updates(self) -> None:
        """Check for updates and prompt the user to update if a new version is available."""
        try:
            response = requests.get(VERSION_URL)
            data = json.loads(response.text)
            latest_version = data["version"]
            if latest_version > CURRENT_VERSION:
                self.logger.info("New version %s available!", latest_version)
                download_url = data["download_url"]

                if input("Do you want to update? (y/n): ").lower() == "y":
                    self.update_app(download_url)
            else:
                self.logger.info("You have the latest version.")
        except Exception as e:
            self.logger.warning("Failed to check for updates: %s", str(e))

    def update_app(self, url: str) -> None:
        """Download the new version and replace the current executable."""
        try:
            response = requests.get(url)
            with open("starfield_saver_new.exe", "wb") as f:
                f.write(response.content)

            # Replace the current executable
            os.rename(sys.executable, "starfield_saver_old.exe")
            os.rename("starfield_saver_new.exe", sys.executable)

            self.logger.info("Update successful! Restarting application...")
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit()
        except Exception as e:
            self.logger.error("Update failed: %s", str(e))

import json
import os
import subprocess
import sys

import requests

from dsutil.log import LocalLogger
from version import CURRENT_VERSION

VERSION_URL = "https://gitlab.dannystewart.com/danny/starfield-saver/-/raw/main/version.json"

OLD_FILENAME = "starfield_saver_old.exe"
NEW_FILENAME = "starfield_saver_new.exe"


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
                self.logger.info(
                    "Starting Starfield Saver v%s. You are on the latest version.", CURRENT_VERSION
                )
        except Exception as e:
            self.logger.warning("Failed to check for updates: %s", str(e))

    def update_app(self, url: str) -> None:
        """Download the new version and replace the current executable."""
        try:
            response = requests.get(url)
            with open(NEW_FILENAME, "wb") as f:
                f.write(response.content)

            # Create a batch file to handle the update
            with open("update.bat", "w") as batch_file:
                batch_file.write(f"""
@echo off
timeout /t 1 /nobreak >nul
del "{sys.executable}"
move "{NEW_FILENAME}" "{sys.executable}"
start "" "{sys.executable}"
del "%~f0"
                """)

            self.logger.info("Update successful! Restarting application...")
            subprocess.Popen("update.bat", shell=True)
            sys.exit()
        except Exception as e:
            self.logger.error("Update failed: %s", str(e))

    def cleanup_old_version(self) -> None:
        """Remove the old version of the executable if it exists."""
        if os.path.exists(OLD_FILENAME):
            try:
                os.remove(OLD_FILENAME)
                self.logger.info("Removed old version: %s", OLD_FILENAME)
            except Exception as e:
                self.logger.error("Failed to remove old version: %s", str(e))

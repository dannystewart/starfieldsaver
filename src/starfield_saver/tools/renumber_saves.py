# ruff: noqa: T201

"""Renumber Starfield saves beginning with the specified save number.

This single-use utility script will renumber Starfield save files (*.sfs) in the specified
directory, starting with the given save number. Everything prior to this number will be left alone.
The script will sort the save files by number, then renumber them sequentially starting from the
given number. The script will skip any files that do not match the expected format or character ID.

Usage: python save_renumberer.py <starting_save_number> [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

SAVE_DIR = Path(r"C:\Users\danny\Documents\My Games\Starfield\Saves")


def safe_int(s: str) -> float:
    """Convert a string to an integer, handling extra digits."""
    if match := re.match(r"Save(\d+)", s):
        num_str = match[1]
        try:
            num = int(num_str)
            # If the number has more than 4 digits, treat it as a 4-digit number
            return int(num_str[:4]) if len(num_str) > 4 else num
        except ValueError:
            return float("inf")
    return float("inf")  # Return a very large number for non-matching files


def renumber_saves(starting_save_number: int, dry_run: bool = True) -> None:
    """Renumber save files in the given directory."""
    # Get all .sfs files in the directory
    save_files = [f.name for f in SAVE_DIR.iterdir() if f.is_file() and f.name.endswith(".sfs")]

    # Sort the files, putting non-matching files at the end
    save_files.sort(key=safe_int)
    # Start numbering from the first save number
    new_number = starting_save_number

    changes = []

    for filename in save_files:
        if match := re.match(r"(Save)(\d+)(_F1C39E63.+\.sfs)", filename):
            prefix, old_number, suffix = match.groups()
            old_number = int(old_number)
            if safe_int(filename) >= starting_save_number:
                new_filename = f"{prefix}{new_number}{suffix}"
                changes.append((filename, new_filename))
                new_number += 1
            else:
                print(f"Skipping {filename} (number < {starting_save_number})")
        else:
            print(f"Skipping {filename} (doesn't match expected format or character ID)")

    print_dry_run_results(changes)

    # If not a dry run, actually perform the renaming
    if not dry_run:
        perform_rename(changes)


def print_dry_run_results(changes: list[tuple[str, str]]) -> None:
    """Print the results of a dry run."""
    print("\nDry Run Results:")
    print("----------------")
    for old, new in changes:
        print(f"{old} -> {new}")

    print(f"\nTotal changes: {len(changes)}")


def perform_rename(changes: list[tuple[str, str]]) -> None:
    """Perform the actual renaming of files."""
    print("\nPerforming actual renaming...")
    for old, new in changes:
        old_path = Path(SAVE_DIR) / old
        new_path = Path(SAVE_DIR) / new
        Path(old_path).rename(new_path)
        print(f"Renamed {old} to {new}")
    print("Renaming complete.")


def main() -> None:
    """Parse command-line arguments and renumber save files."""
    parser = argparse.ArgumentParser(description="Renumber Starfield save files.")
    parser.add_argument("starting_save_number", type=int, help="The starting save number")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without renaming")

    args = parser.parse_args()

    renumber_saves(args.starting_save_number, args.dry_run)


if __name__ == "__main__":
    main()

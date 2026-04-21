import os
from dataclasses import dataclass
from lssql.parser import parse_filename, should_skip


def scan_directory(directory: str) -> list[dict]:
    """
    scan a directory and return a list of dictionaries.
    does not recurse into subdirectories.
    """
    rows = []

    with os.scandir(directory) as entries:
        for entry in entries:

            if not entry.is_file():
                # - skip directories.
                # - cf. `os.scandir` does not return `.` or `..`
                continue

            if should_skip(entry.name):
                continue

            parsed = parse_filename(entry.name)
            parsed["path"] = os.path.dirname(entry.path)  # set relative path
            rows.append(parsed)

    return rows

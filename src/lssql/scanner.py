# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

import os

from lssql.parser import parse_filename, should_skip


def scan_directory(directory: str, recursive: bool = False) -> list[dict]:
    """
    scan a directory and return a list of dictionaries.
    recursive=False by default
    """
    rows = []

    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    rows.extend(scan_directory(entry.path, recursive=True))
                continue

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

import os
from dataclasses import dataclass
from lssql.parser import parse_filename


@dataclass
class FileRow:
    path: str
    size: int
    mtime: float
    parsed: dict


def scan_directory(directory: str) -> list[FileRow]:
    """
    scan a directory and return a list of FileRow.
    does not recurse into subdirectories.
    """
    rows = []

    with os.scandir(directory) as entries:
        for entry in entries:

            if not entry.is_file():
                # - skip directories.
                # - cf. `os.scandir` does not return `.` or `..`
                continue

            stem, _ = os.path.splitext(entry.name)
            if stem and stem.startswith("."):
                # - skip hidden files (.gitignore)
                # - keep other ones including no-extension-files
                continue

            stat = entry.stat()
            parsed = parse_filename(entry.name)

            row = FileRow(
                path=entry.path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                parsed=parsed,
            )
            rows.append(row)

    return rows

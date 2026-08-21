import os
from collections.abc import Iterator

from lssql.parser import parse_filename, should_skip


def walk_files(directory: str, recursive: bool = False) -> Iterator[tuple[str, str]]:
    """
    yield (directory, filename) for every file the tools should look at.

    the single walk under list, harvest, set, verify, and reset. a
    subdirectory is descended only when recursive is set. anything that is
    not a file, and every name should_skip rejects, stops here.
    """
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    yield from walk_files(entry.path, recursive=True)
                continue

            if not entry.is_file():
                # - skip directories.
                # - cf. `os.scandir` does not return `.` or `..`
                continue

            if should_skip(entry.name):
                continue

            # dirname of the entry, not the argument: a trailing slash on the
            # argument would otherwise reach every caller and print doubled
            yield os.path.dirname(entry.path), entry.name


def scan_directory(directory: str, recursive: bool = False) -> list[dict]:
    """
    scan a directory and return a list of dictionaries.
    recursive=False by default
    """
    rows = []

    for found_in, filename in walk_files(directory, recursive=recursive):
        parsed = parse_filename(filename)
        parsed["path"] = found_in
        rows.append(parsed)

    return rows

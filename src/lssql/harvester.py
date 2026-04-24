import os
from datetime import datetime

SEPARATOR = "^^^"


def harvest_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def is_troublesome_name(filename: str) -> bool:
    stem, _ = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)
    if len(parts) > 3:
        return True
    return False


def is_already_harvested(filename: str) -> bool:
    stem, _ = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)
    if len(parts) < 2:
        return False
    if parts[1] in ["^", "^^"]:
        return False
    return len(parts[1]) > 0


def build_harvested_filename(filename: str) -> str:
    stem, ext = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)

    original = parts[0]
    comment = parts[2] if len(parts) > 2 else ""

    hd_tag = f"ls:hd={harvest_date()}"

    if comment:
        return f"{original}{SEPARATOR}{hd_tag}{SEPARATOR}{comment}{ext}"
    return f"{original}{SEPARATOR}{hd_tag}{ext}"


def harvest_file(directory: str, filename: str, commit: bool) -> dict:
    """
    Process a single file. Returns a result dict describing what happened.
    commit=False is dry-run (default, safe).
    """
    if is_troublesome_name(filename):
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "filename not supported",
        }

    if is_already_harvested(filename):
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "already harvested",
        }

    new_filename = build_harvested_filename(filename)
    old_path = os.path.join(directory, filename)
    new_path = os.path.join(directory, new_filename)

    if commit:
        os.rename(old_path, new_path)
        return {
            "directory": directory,
            "file": filename,
            "status": "renamed",
            "new_name": new_filename,
        }
    else:
        return {
            "directory": directory,
            "file": filename,
            "status": "dry-run",
            "new_name": new_filename,
        }


def harvest_directory(
    path: str, commit: bool, recursive: bool = False, max_files: int = 0
) -> list[dict]:
    """
    Recursively harvest files and returns results.
    Returned results are recursively extended to its parent.
    'max_files = 0' means no limit -- zero is falsy in Python so
        'if max_files' is the clean guard.
    """
    results = []

    with os.scandir(path) as entries:
        for entry in entries:
            if max_files and len(results) >= max_files:
                break

            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    remaining = max_files - len(results) if max_files else 0
                    results.extend(
                        harvest_directory(entry.path, commit, recursive, remaining)
                    )
                continue

            if not entry.is_file():
                continue

            filename = entry.name

            # skip hidden files
            if filename.startswith("."):
                continue

            # skip files without extensions
            _, ext = os.path.splitext(filename)
            if not ext:
                continue

            result = harvest_file(path, filename, commit)
            results.append(result)

    results.sort(key=lambda d: (d["directory"], d["file"]))
    return results


def remove_tags_from_filename(filename: str) -> str:
    """
    strip harvested tags from filename, restore original.
    'photo^^^ls:hd=20260422.jpg' -> 'photo.jpg'
    right of second ^^^ (human comment) is preserved.
    """
    stem, ext = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)

    original = parts[0]
    comment = parts[2] if len(parts) > 2 else ""

    if comment:
        return f"{original}{SEPARATOR}{SEPARATOR}{comment}{ext}"
    return f"{original}{ext}"


def remove_tags_from_directory(
    path: str, commit: bool, recursive: bool = False
) -> list[dict]:
    results = []

    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    results.extend(
                        remove_tags_from_directory(entry.path, commit, recursive)
                    )
                continue

            if not entry.is_file():
                continue

            filename = entry.name

            if filename.startswith("."):
                continue

            _, ext = os.path.splitext(filename)
            if not ext:
                continue

            if is_troublesome_name(filename):
                results.append(
                    {
                        "directory": path,
                        "file": filename,
                        "status": "skipped",
                        "reason": "filename not supported",
                    }
                )
                continue

            if not is_already_harvested(filename):
                results.append(
                    {
                        "directory": path,
                        "file": filename,
                        "status": "skipped",
                        "reason": "not harvested",
                    }
                )
                continue

            new_filename = remove_tags_from_filename(filename)
            old_path = os.path.join(path, filename)
            new_path = os.path.join(path, new_filename)

            if commit:
                os.rename(old_path, new_path)
                results.append(
                    {
                        "directory": path,
                        "file": filename,
                        "status": "restored",
                        "new_name": new_filename,
                    }
                )
            else:
                results.append(
                    {
                        "directory": path,
                        "file": filename,
                        "status": "dry-run",
                        "new_name": new_filename,
                    }
                )

    results.sort(key=lambda d: (d["directory"], d["file"]))
    return results

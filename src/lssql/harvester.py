import os

from lssql.harvester_au import build_au_tag_string
from lssql.harvester_ex import build_ex_tag_string
from lssql.harvester_ls import content_hash, extract_dimension, harvest_date
from lssql.harvester_util import (
    DEFAULT_HARVEST_EXTS,
    is_already_harvested,
    is_troublesome_name,
)
from lssql.harvester_zi import build_zi_tag_string
from lssql.parser import SEPARATOR, join_hatfile_name
from lssql.scanner import walk_files


def build_harvested_filename(filename: str, directory: str = "") -> str:
    """
    build the harvested name for a file: original^^^tags^^^comment.ext.

    directory is optional. without it no file is opened, so every tag read
    from content is left out and only the harvest date remains.
    """
    stem, ext = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)

    original = parts[0]
    comment = parts[2] if len(parts) > 2 else ""

    filepath = os.path.join(directory, filename) if directory else ""

    hd_tag = f"ls:hd={harvest_date()}"
    fh_tag = f"ls:fh={content_hash(filepath)}" if filepath else ""
    width, height = extract_dimension(filepath, ext) if filepath else ("", "")
    dw_tag = f"ls:dw={width}" if width else ""
    dh_tag = f"ls:dh={height}" if height else ""
    au_tags = build_au_tag_string(filepath, ext) if filepath else ""
    ex_tags = build_ex_tag_string(filepath, ext) if filepath else ""
    zi_tags = build_zi_tag_string(filepath, ext) if filepath else ""

    tags = "^".join(
        filter(None, [hd_tag, fh_tag, dw_tag, dh_tag, au_tags, ex_tags, zi_tags])
    )

    return join_hatfile_name(original, tags, comment, ext)


def harvest_file(
    directory: str, filename: str, commit: bool, allowed_exts: set | None = None
) -> dict:
    """
    Process a single file. Returns a result dict describing what happened.
    commit=False is dry-run (default, safe).
    """
    stem, ext = os.path.splitext(filename)

    effective_exts = allowed_exts if allowed_exts else DEFAULT_HARVEST_EXTS

    if ext.lower() not in effective_exts:
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "extension not in whitelist or --ext list",
        }

    # checked before is_troublesome_name so the specific reason wins: a plain
    # name with a stray caret and no separator is not a malformed Hatfile, it
    # is a file the user should rename first.
    if SEPARATOR not in stem and "^" in stem:
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "caret in filename -- rename file before harvesting",
        }

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

    if len(stem) > 80:
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": f"filename too long to harvest ({len(stem)} chars, 80 max)",
        }

    new_filename = build_harvested_filename(filename, directory)
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
    path: str,
    commit: bool,
    recursive: bool = False,
    max_files: int = 0,
    allowed_exts: set | None = None,
) -> list[dict]:
    """
    Recursively harvest files and returns results.
    'max_files = 0' means no limit, and a negative limit harvests nothing.
    An empty or absent allowed_exts means no filter, accept all.

    max_files counts the files actioned. a skipped file is still reported and
    does not spend the budget, and the budget holds across the whole walk
    rather than per directory. See DESIGN.md, "--max counts what it actions".
    """
    if max_files < 0:
        return []

    results = []
    actioned = 0

    for directory, filename in walk_files(path, recursive=recursive):
        result = harvest_file(directory, filename, commit, allowed_exts)
        results.append(result)

        if result["status"] == "skipped":
            continue

        actioned += 1
        if max_files and actioned >= max_files:
            break

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

    return join_hatfile_name(original, "", comment, ext)


def remove_tags_from_filename_commit(path: str, filename: str, commit: bool) -> dict:
    """
    strip the tags from one file, and under commit rename it on disk.
    returns a result dict -- same shape as harvest_file results.
    """
    new_filename = remove_tags_from_filename(filename)
    old_path = os.path.join(path, filename)
    new_path = os.path.join(path, new_filename)

    status = "dry-run"
    if commit:
        os.rename(old_path, new_path)
        status = "restored"

    return {
        "directory": path,
        "file": filename,
        "status": status,
        "new_name": new_filename,
    }


def remove_tags_from_directory(
    path: str, commit: bool, recursive: bool = False
) -> list[dict]:
    """
    strip harvested tags from every file in a directory.
    a name that cannot be read back, and a file that was never harvested,
    are both reported as skipped rather than touched.
    """
    results = []

    for directory, filename in walk_files(path, recursive=recursive):
        if is_troublesome_name(filename):
            results.append(
                {
                    "directory": directory,
                    "file": filename,
                    "status": "skipped",
                    "reason": "filename not supported",
                }
            )
            continue

        if not is_already_harvested(filename):
            results.append(
                {
                    "directory": directory,
                    "file": filename,
                    "status": "skipped",
                    "reason": "not harvested",
                }
            )
            continue

        results.append(remove_tags_from_filename_commit(directory, filename, commit))

    results.sort(key=lambda d: (d["directory"], d["file"]))
    return results


def verify_file(directory: str, filename: str) -> dict:
    """
    compare ls:fh in filename against current file content hash.
    read-only, never touches files.
    """
    filepath = os.path.join(directory, filename)

    if not is_already_harvested(filename):
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "no ls:fh -- harvest first",
        }

    stem, _ = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)
    tags_str = parts[1] if len(parts) > 1 else ""
    stored_fh = None

    for tag in tags_str.split("^"):
        if tag.startswith("ls:fh="):
            stored_fh = tag[len("ls:fh=") :]
            break

    if not stored_fh:
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "no ls:fh -- harvest first",
        }

    actual_fh = content_hash(filepath)

    if stored_fh == actual_fh:
        return {
            "directory": directory,
            "file": filename,
            "status": "ok",
        }
    else:
        return {
            "directory": directory,
            "file": filename,
            "status": "changed",
            "stored": stored_fh,
            "actual": actual_fh,
        }


def verify_directory(path: str, recursive: bool = False) -> list[dict]:
    """
    verify ls:fh tags in a directory against current file content.
    read-only, never touches files.
    """
    results = [
        verify_file(directory, filename)
        for directory, filename in walk_files(path, recursive=recursive)
    ]

    results.sort(key=lambda d: (d["directory"], d["file"]))
    return results

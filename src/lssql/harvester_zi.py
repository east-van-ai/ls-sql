# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
ZIP metadata extraction
"""

import zipfile

from lssql.harvester_util import tags_to_string

SUPPORTED_ZIP_EXTS = {".zip", ".cbz"}


def _is_resource_fork(entry) -> bool:
    """
    filter out macOS AppleDouble resource fork entries.
    these are implementation noise, not real content.
    __MACOSX/ directory and ._filename sidecar files.
    """
    name = entry.filename
    return name.startswith("__MACOSX/") or name.rsplit("/", 1)[-1].startswith("._")


def _parent_segments(filepath: str) -> set[str]:
    """
    extract all parent directory segments from a file path inside a ZIP.
    'photos/sub/a.jpg' -> {'photos', 'photos/sub'}
    these are implicit directories -- they may not have explicit entries.
    """
    parts = filepath.split("/")
    segments = set()
    for i in range(1, len(parts)):
        segment = "/".join(parts[:i])
        if segment:
            segments.add(segment)
    return segments


def _extract_zip_tags(filepath: str) -> dict:
    """
    extract metadata from a ZIP file via the central directory.
    no decompression required.

    zi:cnt   total entry count (files and directories, including dot entries)
    zi:ext   content types, comma-separated extensions, no dots (e.g. jpg,png,txt)
             directories excluded -- extensions only make sense for files
    zi:dot   dot entry count (files and directories starting with a dot)
             only present when > 0 -- presence alone is the signal
    zi:dir   directory count -- explicit and implicit combined, deduplicated
             explicit: entries whose name ends with /
             implicit: parent path segments inferred from file entries
             NOTE: ZIP directories are optional entries (name ending with /).
             many tools omit them entirely and only write file entries.
             counting implicit dirs ensures zi:dir reflects actual structure.
             a ZIP can also contain thousands of empty explicit directories
             with no file entries at all -- both cases are handled correctly.
    """
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            entries = [e for e in zf.infolist() if not _is_resource_fork(e)]
    except zipfile.BadZipFile, OSError:
        return {}

    if not entries:
        return {}

    files = [e for e in entries if not e.is_dir()]
    cnt = len(files)

    exts = sorted(
        {
            e.filename.rsplit(".", 1)[-1].lower()
            for e in entries
            if not e.is_dir() and "." in e.filename.rsplit("/", 1)[-1]
        }
    )

    dot_count = sum(
        1 for e in entries if e.filename.rstrip("/").rsplit("/", 1)[-1].startswith(".")
    )

    explicit_dirs = {e.filename.rstrip("/") for e in entries if e.is_dir()}
    implicit_dirs = {
        segment
        for e in entries
        if not e.is_dir()
        for segment in _parent_segments(e.filename)
    }
    dir_count = len(explicit_dirs | implicit_dirs)

    tags = {}
    tags["zi:cnt"] = str(cnt)
    if exts:
        tags["zi:ext"] = ";".join(exts)
    if dot_count:
        tags["zi:dot"] = str(dot_count)
    tags["zi:dir"] = str(dir_count)

    return tags


def build_zi_tag_string(filepath: str, ext: str) -> str:
    """
    return a ^-separated tag string for ZIP files.
    returns empty string for non-ZIP or on failure.
    """
    if ext.lower() not in SUPPORTED_ZIP_EXTS:
        return ""

    tags = _extract_zip_tags(filepath)
    if not tags:
        return ""

    return tags_to_string(tags)

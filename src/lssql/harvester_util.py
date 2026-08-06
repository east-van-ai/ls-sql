# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

import os

SEPARATOR = "^^^"


DEFAULT_HARVEST_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp3",
    ".m4a",
    ".zip",
    ".cbz",
}


def sanitize_tag_value(value: str) -> str:
    """
    replace caret characters in tag values before encoding into filename.
    ^ is the tag separator. any caret in a value corrupts the filename format.
    ; is the list separator and treated in the same way.
    """
    return value.replace("^", "-").replace(";", "-")


def is_troublesome_name(filename: str) -> bool:
    stem, _ = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)
    return len(parts) > 3


def is_already_harvested(filename: str) -> bool:
    stem, _ = os.path.splitext(filename)
    parts = stem.split(SEPARATOR)
    if len(parts) < 2:
        return False
    if parts[1] in ["^", "^^"]:
        return False
    return len(parts[1]) > 0


def tags_to_string(tags: dict) -> str:
    """
    join a tag dict into a ^-separated 'key=value' string.
    empty dict -> empty string.
    """
    return "^".join(f"{k}={v}" for k, v in tags.items())


def parse_ext_filter(ext_filter: str) -> set[str]:
    """
    parse extension string into a set of lowercase dotted extensions.
    semicolon or comma separated.
    'jpg;png' or 'jpg,png' -> {'.jpg', '.png'}
    '' -> set()  -- empty means no filter, use DEFAULT_HARVEST_EXTS
    """
    if not ext_filter:
        return set()
    return {
        f".{e.strip().lower().lstrip('.')}"
        for e in ext_filter.replace(",", ";").split(";")
    }

import os

from lssql.parser import SEPARATOR, is_hatfile_stem

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
    """
    report whether a filename is one the harvester must not rewrite.
    a stem that is not a Hatfile stem cannot be read back confidently,
    so renaming it risks losing the part that did not parse.
    """
    stem, _ = os.path.splitext(filename)
    return not is_hatfile_stem(stem, SEPARATOR)


def is_already_harvested(filename: str) -> bool:
    """
    report whether a filename already carries a tag section.
    a malformed stem is never 'already harvested': its tag part is a stray
    caret run rather than tags, and treating it as tags is what let `set`
    overwrite the section and drop the text.
    """
    stem, _ = os.path.splitext(filename)
    if not is_hatfile_stem(stem, SEPARATOR):
        return False
    parts = stem.split(SEPARATOR)
    if len(parts) < 2:
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

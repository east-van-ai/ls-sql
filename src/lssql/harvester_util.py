import os

SEPARATOR = "^^^"


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


def parse_ext_filter(ext_filter: str) -> set[str]:
    """
    parse comma-separated extension string into a set of lowercase dotted extensions.
    'jpg,png' -> {'.jpg', '.png'}
    '' -> set()  -- empty means no filter, accept all
    """
    if not ext_filter:
        return set()
    return {f".{e.strip().lower().lstrip('.')}" for e in ext_filter.split(",")}

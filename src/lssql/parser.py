SEPARATOR = "^^^"


def parse_filename(filename: str) -> dict:
    """
    parse a filename into its components.
    returns a dict with original, tags, and comment.

    original^^^raw_tags^^^comment.ext
    """
    stem, ext = split_extension(filename)

    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)

    tags = parse_tags(raw_tags)

    harvested = not (original is None or original == stem)

    data = {
        "path": "",
        "original": original,
        "tags": tags,  # dict
        "comment": comment,
        "ext": ext,
        "harvested": harvested,
        "filename": filename,
    }

    return data


def parse_tags(raw: str) -> dict:
    """
    parse tag string into a dict.
    'ls:hd=20260503^ls:fh=03754271b00a0e1c' -> {'ls:hd': '20260503', 'ls:fh': '03754271b00a0e1c'}
    """
    tags = {}
    if not raw:
        return tags
    for pair in raw.split("^"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            tags[key.strip()] = value.strip()
    return tags


def is_hatfile_stem(stem: str, separator: str = SEPARATOR) -> bool:
    """
    report whether a stem is a well-formed Hatfile stem.

    a stray caret is the thing this catches. splitting on '^^^' alone is
    greedy from the left, so an odd caret stays glued to the front of the
    next field and '0001-01234^^^^it-is-blue' reads as tags of '^it-is-blue'.
    """

    parts = stem.split(separator)

    if len(parts) > 3:
        return False

    original = parts[0]
    raw_tags = parts[1] if len(parts) > 1 else ""
    comment = parts[2] if len(parts) > 2 else ""

    if "^" in original or "^" in comment:
        return False

    # '^' is the tag delimiter, so carets are legal in the tag part. a leading,
    # trailing, or doubled one is not: it opens an empty segment.
    return raw_tags == "" or "" not in raw_tags.split("^")


def split_filename_stem(stem: str, separator: str) -> tuple:
    """
    split a filename stem into (original, raw_tags, comment).
    * caller must strip any directory components from stem before invoking.
    * when stem is not a Hatfile stem, return it whole as 'original'.
    """

    if not is_hatfile_stem(stem, separator):
        return stem, "", ""

    parts = stem.split(separator)

    original = parts[0]
    raw_tags = parts[1] if len(parts) > 1 else ""
    comment = parts[2] if len(parts) > 2 else ""

    return original, raw_tags, comment


def join_hatfile_name(original: str, tags: str, comment: str, ext: str) -> str:
    """
    assemble a filename from its Hatfile components. the inverse of
    split_filename_stem, with the extension put back on.

    a comment sits right of the second ^^^, so it needs both boundaries even
    when the tag section between them is empty. with neither a comment nor
    tags there is no boundary to draw, and the name is the plain original.
    """
    if comment:
        return f"{original}{SEPARATOR}{tags}{SEPARATOR}{comment}{ext}"
    if tags:
        return f"{original}{SEPARATOR}{tags}{SEPARATOR}{ext}"
    return f"{original}{ext}"


def split_path(filename_with_path: str) -> tuple:
    """
    return (directory, filename)
    """
    slash = filename_with_path.rfind("/")  # last slash
    if slash == -1:
        return "", filename_with_path  # no directory

    # split before and after the slash
    return filename_with_path[:slash], filename_with_path[slash + 1 :]


def split_extension(filename: str) -> tuple:
    """
    split filename into stem and extension.
    extension is the right most word after the right most period.
    extension includes a period.
    no extension means empty string.

    'foo'         -> ('foo',     '')
    'foo.png'     -> ('foo',     '.png')
    'foo.poo.png' -> ('foo.poo', '.png')
    """
    dot = filename.rfind(".")
    if dot == -1:
        return filename, ""
    return filename[:dot], filename[dot:]


# '.' and '..' are directory navigation entries, not files.
# '' is empty string and is not a file either.
# skip them silently. they are not part of the output.
SKIP = {None, "", ".", ".."}


def should_skip(filename: str) -> bool:
    """
    return True if the file should be ignored.
    * caller must strip any directory components from filename before invoking.

    Hidden or no extension files -- skipped silently.
        Out of scope by design.
    """
    if filename in SKIP:  # explicitly listed to skip
        return True

    stem, ext = split_extension(filename)  # ext includes the dot

    is_hidden = stem == "" or stem.startswith(".")
    has_no_extension = ext in ("", ".")

    return is_hidden or has_no_extension


def build_file_path(parsed: dict) -> str:
    """combine `path` and `filename` into a string."""
    path = f"{parsed.get('path')}/" if parsed.get("path") else ""
    return f"{path}{parsed.get('filename')}"

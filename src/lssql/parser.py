# parser.py

SEPARATOR = "^^^"


def parse_filename(filename: str) -> dict:
    """
    parse a filename into its components.
    returns a dict with original, tags, and comment.
    """
    stem, ext = split_extension(filename)

    original, raw_tags, comment = split_filename_stem(stem, SEPARATOR)

    tags = parse_tags(raw_tags)

    harvested = not (original is None or original == stem)

    data = {
        "original": original,
        "tags": tags,
        "comment": comment,
        "ext": ext,
        "harvested": harvested,
    }

    return data


def parse_tags(raw: str) -> dict:
    """
    parse tag string into a dict.
    'sd:mn=sdxl^ls:fh=a3f2c8f91b' -> {'sd:mn': 'sdxl', 'ls:fh': 'a3f2c8f91b'}
    """
    tags = {}
    if not raw:
        return tags
    for pair in raw.split("^"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            tags[key.strip()] = value.strip()
    return tags


def split_filename_stem(stem: str, separator: str) -> tuple:
    """
    split filename stem into 3 sections(original, raw_tags, comment)
    if stem is to be skipped, return None values
    if stem has too many separators, return parameter value as original
    """
    if should_skip(stem):
        return None, None, None

    if stem.count(separator) > 2:
        return stem, "", ""

    parts = stem.split(separator)

    original = parts[0]
    raw_tags = parts[1] if len(parts) > 1 else ""
    comment = parts[2] if len(parts) > 2 else ""

    return original, raw_tags, comment


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
    return filename in SKIP

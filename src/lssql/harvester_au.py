# harvester_au.py -- audio metadata extraction (MP3, etc.)

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen._util import MutagenError


def extract_mp3_tags(filepath: str) -> dict:
    """
    extract audio metadata from an MP3 file.
    returns a dict of au: tags. empty dict on failure or missing tags.

    au:ar    Artist
    au:al    Album
    au:tt    Track title
    au:tn    Track number
    au:yr    Year
    """
    try:
        audio = EasyID3(filepath)
    except MutagenError:
        return {}

    def get(key):
        values = audio.get(key)
        return values[0] if values else ""

    tags = {}

    ar = get("artist")
    al = get("album")
    tt = get("title")
    tn = get("tracknumber")
    yr = get("date")

    if ar:
        tags["au:ar"] = ar
    if al:
        tags["au:al"] = al
    if tt:
        tags["au:tt"] = tt
    if tn:
        tags["au:tn"] = tn.split("/")[0]  # '1/12' -> '1'
    if yr:
        tags["au:yr"] = yr[:4]  # '2026-01-01' -> '2026'

    return tags


def build_au_tag_string(filepath: str, ext: str) -> str:
    """
    return a ^-separated tag string for supported audio formats.
    returns empty string for unsupported formats or on failure.
    """
    if ext.lower() != ".mp3":
        return ""

    tags = extract_mp3_tags(filepath)
    if not tags:
        return ""

    return "^".join(f"{k}={v}" for k, v in tags.items())

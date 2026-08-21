"""
audio metadata extraction (MP3, M4A)
"""

from mutagen._util import MutagenError

from lssql.harvester_util import sanitize_tag_value, tags_to_string

SUPPORTED_AUDIO_EXTS = {".mp3", ".m4a"}


def build_au_tag_string(filepath: str, ext: str) -> str:
    """
    return a ^-separated tag string for supported audio formats.
    returns empty string for unsupported formats or on failure.
    """
    if ext.lower() not in SUPPORTED_AUDIO_EXTS:
        return ""
    # the guard above leaves the two supported extensions, and nothing else
    if ext.lower() == ".mp3":
        tags = _extract_mp3_tags(filepath)
    else:
        tags = _extract_m4a_tags(filepath)
    return tags_to_string(tags)


def _extract_mp3_tags(filepath: str) -> dict:
    """
    extract audio metadata from an MP3 file via EasyID3.
    returns a dict of au: tags. empty dict on failure or missing tags.
    """
    try:
        from mutagen.easyid3 import EasyID3

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
        tags["au:ar"] = sanitize_tag_value(ar)
    if al:
        tags["au:al"] = sanitize_tag_value(al)
    if tt:
        tags["au:tt"] = sanitize_tag_value(tt)
    if tn:
        tags["au:tn"] = tn.split("/")[0]  # '1/12' -> '1'
    if yr:
        tags["au:yr"] = yr[:4]  # '2026-01-01' -> '2026'

    return tags


def _extract_m4a_tags(filepath: str) -> dict:
    """
    extract audio metadata from an M4A file via MP4 iTunes atoms.
    returns a dict of au: tags. empty dict on failure or missing tags.
    """
    try:
        from mutagen.mp4 import MP4

        audio = MP4(filepath)
        itags = audio.tags or {}
    except MutagenError:
        return {}

    def get(key):
        values = itags.get(key)
        return str(values[0]) if values else ""

    tags = {}

    ar = get("\xa9ART")
    al = get("\xa9alb")
    tt = get("\xa9nam")
    yr = get("\xa9day")
    trkn = itags.get("trkn")

    if ar:
        tags["au:ar"] = sanitize_tag_value(ar)
    if al:
        tags["au:al"] = sanitize_tag_value(al)
    if tt:
        tags["au:tt"] = sanitize_tag_value(tt)
    if yr:
        tags["au:yr"] = yr[:4]
    if trkn:
        tags["au:tn"] = str(trkn[0][0])  # [(3, 0)] -> '3'

    return tags

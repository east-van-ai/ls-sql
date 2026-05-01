"""
audio metadata extraction (MP3, M4A)
"""

from mutagen._util import MutagenError

SUPPORTED_AUDIO_EXTS = {".mp3", ".m4a"}


def build_au_tag_string(filepath: str, ext: str) -> str:
    """
    return a ^-separated tag string for supported audio formats.
    returns empty string for unsupported formats or on failure.
    """
    if ext.lower() not in SUPPORTED_AUDIO_EXTS:
        return ""
    if ext.lower() == ".mp3":
        tags = _extract_mp3_tags(filepath)
    elif ext.lower() == ".m4a":
        tags = _extract_m4a_tags(filepath)
    else:
        return ""
    return "^".join(f"{k}={v}" for k, v in tags.items())


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
        tags["au:ar"] = ar
    if al:
        tags["au:al"] = al
    if tt:
        tags["au:tt"] = tt
    if yr:
        tags["au:yr"] = yr[:4]
    if trkn:
        tags["au:tn"] = str(trkn[0][0])  # [(3, 0)] -> '3'

    return tags

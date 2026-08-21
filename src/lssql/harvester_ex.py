"""
EXIF metadata extraction for JPG files
"""

import piexif

from lssql.harvester_util import sanitize_tag_value, tags_to_string


def _safe(d, ifd, tag):
    """safely extract a tag value from an EXIF IFD dict."""
    try:
        return d[ifd][tag]
    except KeyError, TypeError:
        return None


def _rational(value) -> str:
    """
    format an EXIF rational as a trimmed decimal string.
    (28, 10) -> '2.8', (50, 1) -> '50'
    """
    numerator, denominator = value
    return f"{numerator / denominator:.1f}".rstrip("0").rstrip(".")


def extract_jpg_tags(filepath: str) -> dict:
    """
    extract EXIF metadata from a JPG file.
    returns a dict of ex: tags. empty dict on failure or missing tags.

    ex:dto   DateTimeOriginal (YYYY:MM:DD)
    ex:cam   camera model, slugified (e.g. canon-r5)
    ex:iso   ISO value
    ex:ap    aperture (e.g. f2.8)
    ex:fl    focal length (e.g. 50mm)
    """
    try:
        exif = piexif.load(filepath)
    except Exception:  # noqa: BLE001 -- unreadable EXIF is not an error
        return {}

    tags = {}

    # ex:dto -- DateTimeOriginal
    dto = _safe(exif, "Exif", piexif.ExifIFD.DateTimeOriginal)
    if dto:
        try:
            date_str = dto.decode("utf-8")  # '2024:07:12 14:30:00'
            tags["ex:dto"] = sanitize_tag_value(date_str[:10])  # '2024:07:12'
        except Exception:  # noqa: BLE001, S110 -- a bad field yields no tag
            pass

    # ex:cam -- camera model
    cam = _safe(exif, "0th", piexif.ImageIFD.Model)
    if cam:
        try:
            cam_str = cam.decode("utf-8").strip().lower()
            cam_str = cam_str.replace(" ", "-").replace("_", "-")
            tags["ex:cam"] = sanitize_tag_value(cam_str)
        except Exception:  # noqa: BLE001, S110 -- a bad field yields no tag
            pass

    # ex:iso -- ISO speed
    iso = _safe(exif, "Exif", piexif.ExifIFD.ISOSpeedRatings)
    if iso:
        tags["ex:iso"] = str(iso)

    # ex:ap -- aperture (FNumber as rational)
    ap = _safe(exif, "Exif", piexif.ExifIFD.FNumber)
    if ap:
        try:
            tags["ex:ap"] = f"f{_rational(ap)}"  # f2.8, not f2.800000
        except Exception:  # noqa: BLE001, S110 -- a bad field yields no tag
            pass

    # ex:fl -- focal length (rational)
    fl = _safe(exif, "Exif", piexif.ExifIFD.FocalLength)
    if fl:
        try:
            tags["ex:fl"] = f"{_rational(fl)}mm"
        except Exception:  # noqa: BLE001, S110 -- a bad field yields no tag
            pass

    return tags


def build_ex_tag_string(filepath: str, ext: str) -> str:
    """
    return a ^-separated tag string for supported image formats.
    returns empty string for unsupported formats or on failure.
    """
    if ext.lower() not in (".jpg", ".jpeg"):
        return ""

    tags = extract_jpg_tags(filepath)
    if not tags:
        return ""

    return tags_to_string(tags)

"""
EXIF metadata extraction for JPG files
"""

import piexif


def _safe(d, ifd, tag):
    """safely extract a tag value from an EXIF IFD dict."""
    try:
        return d[ifd][tag]
    except KeyError, TypeError:
        return None


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
    except Exception:
        return {}

    tags = {}

    # ex:dto -- DateTimeOriginal
    dto = _safe(exif, "Exif", piexif.ExifIFD.DateTimeOriginal)
    if dto:
        try:
            date_str = dto.decode("utf-8")  # '2024:07:12 14:30:00'
            tags["ex:dto"] = date_str[:10]  # '2024:07:12'
        except Exception:
            pass

    # ex:cam -- camera model
    cam = _safe(exif, "0th", piexif.ImageIFD.Model)
    if cam:
        try:
            cam_str = cam.decode("utf-8").strip().lower()
            cam_str = cam_str.replace(" ", "-").replace("_", "-")
            tags["ex:cam"] = cam_str
        except Exception:
            pass

    # ex:iso -- ISO speed
    iso = _safe(exif, "Exif", piexif.ExifIFD.ISOSpeedRatings)
    if iso:
        tags["ex:iso"] = str(iso)

    # ex:ap -- aperture (FNumber as rational)
    ap = _safe(exif, "Exif", piexif.ExifIFD.FNumber)
    if ap:
        try:
            numerator, denominator = ap
            value = numerator / denominator
            # format cleanly: f2.8 not f2.800000
            formatted = f"{value:.1f}".rstrip("0").rstrip(".")
            tags["ex:ap"] = f"f{formatted}"
        except Exception:
            pass

    # ex:fl -- focal length (rational)
    fl = _safe(exif, "Exif", piexif.ExifIFD.FocalLength)
    if fl:
        try:
            numerator, denominator = fl
            value = numerator / denominator
            formatted = f"{value:.1f}".rstrip("0").rstrip(".")
            tags["ex:fl"] = f"{formatted}mm"
        except Exception:
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

    return "^".join(f"{k}={v}" for k, v in tags.items())

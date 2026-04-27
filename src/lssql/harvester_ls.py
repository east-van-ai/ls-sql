from datetime import datetime
from PIL import Image, UnidentifiedImageError

import hashlib

# ------------------------------------------------------------
# Supported image file extensions
# ------------------------------------------------------------
RESOLUTION_EXTS = {
    ".jpg",  # JPEG (baseline)
    ".jpeg",  # JPEG (extended)
    ".png",  # Portable Network Graphics
    ".gif",  # Graphics Interchange Format
    ".webp",  # WebP (modern, lossless or lossy)
}


def extract_resolution(filepath: str, ext: str) -> str:
    """
    extract image resolution using Pillow.
    returns 'WxH' string or empty string on failure.
    supports JPG, PNG, GIF, WEBP.
    """
    if ext.lower() not in RESOLUTION_EXTS:
        return ""

    try:
        with Image.open(filepath) as img:
            w, h = img.size
            return f"{w}x{h}"

    except UnidentifiedImageError, Exception:
        return ""


def harvest_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def content_hash(filepath: str) -> str:
    """SHA256 of file content, first 10 chars."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:10]

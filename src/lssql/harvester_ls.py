# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

import hashlib
from datetime import datetime

from PIL import Image

# ------------------------------------------------------------
# Supported image file extensions
# ------------------------------------------------------------
DIMENSION_EXTS = {
    ".jpg",  # JPEG (baseline)
    ".jpeg",  # JPEG (extended)
    ".png",  # Portable Network Graphics
    ".gif",  # Graphics Interchange Format
    ".webp",  # WebP (modern, lossless or lossy)
}


def extract_dimension(filepath: str, ext: str) -> tuple[str, str]:
    """
    extract image dimension using Pillow.
    returns width and height string or empty strings on failure.
    """
    if ext.lower() not in DIMENSION_EXTS:
        return "", ""
    try:
        with Image.open(filepath) as img:
            w, h = img.size
            return str(w), str(h)
    # UnidentifiedImageError is a subclass of Exception, so catching Exception
    # alone is the same net, minus the redundancy.
    except Exception:  # noqa: BLE001 -- any decode failure means no dimensions
        return "", ""


def harvest_date() -> str:
    # local date on purpose: the tag records the day the file was harvested
    # on this machine, not a UTC instant.
    return datetime.now().strftime("%Y%m%d")  # noqa: DTZ005


def content_hash(filepath: str) -> str:
    """SHA256 of file content, first 16 chars."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

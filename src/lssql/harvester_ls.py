# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

from datetime import datetime
from PIL import Image, UnidentifiedImageError

import hashlib

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
    except UnidentifiedImageError, Exception:
        return "", ""


def harvest_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def content_hash(filepath: str) -> str:
    """SHA256 of file content, first 16 chars."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

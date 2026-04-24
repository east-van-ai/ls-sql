from datetime import datetime
import hashlib


def harvest_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def content_hash(filepath: str) -> str:
    """SHA256 of file content, first 10 chars."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:10]

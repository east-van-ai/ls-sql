"""
tests for lssql.harvester with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
* 'freeze_date' -- a custom pytest fixture defined in 'conftest.py'
"""

from PIL import Image

import lssql.harvester as harvester
from lssql.harvester import content_hash
from lssql.harvester_ls import extract_resolution

# -- harvest_date --


def test_harvest_date(freeze_date):
    """harvest_date() must be called via the module, not imported directly, while freeze_date is active."""
    assert len(harvester.harvest_date()) == 8
    assert harvester.harvest_date().isdigit()
    assert harvester.harvest_date() == "20260421"


# -- content_hash --


def test_content_hash_length(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = content_hash(str(f))
    assert len(result) == 10


def test_content_hash_is_hex(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = content_hash(str(f))
    assert all(c in "0123456789abcdef" for c in result)


def test_content_hash_same_content_same_hash(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_text("same content")
    b.write_text("same content")
    assert content_hash(str(a)) == content_hash(str(b))


def test_content_hash_different_content_different_hash(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_text("content a")
    b.write_text("content b")
    assert content_hash(str(a)) != content_hash(str(b))


# -- extract_resolution --


def make_image(path, size, format):
    """create a valid image file using Pillow."""
    img = Image.new("RGB", size, color=(128, 128, 128))
    img.save(str(path), format=format)
    return str(path)


def test_extract_resolution_jpg(tmp_path):
    filepath = make_image(tmp_path / "photo.jpg", (1920, 1080), "JPEG")
    assert extract_resolution(filepath, ".jpg") == "1920x1080"


def test_extract_resolution_jpeg_ext(tmp_path):
    filepath = make_image(tmp_path / "photo.jpeg", (800, 600), "JPEG")
    assert extract_resolution(filepath, ".jpeg") == "800x600"


def test_extract_resolution_png(tmp_path):
    filepath = make_image(tmp_path / "photo.png", (512, 768), "PNG")
    assert extract_resolution(filepath, ".png") == "512x768"


def test_extract_resolution_gif(tmp_path):
    filepath = make_image(tmp_path / "anim.gif", (320, 240), "GIF")
    assert extract_resolution(filepath, ".gif") == "320x240"


def test_extract_resolution_webp(tmp_path):
    filepath = make_image(tmp_path / "photo.webp", (1280, 720), "WEBP")
    assert extract_resolution(filepath, ".webp") == "1280x720"


def test_extract_resolution_unsupported_ext(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_text("x")
    assert extract_resolution(str(f), ".pdf") == ""


def test_extract_resolution_mp3_skipped(tmp_path):
    f = tmp_path / "song.mp3"
    f.write_text("x")
    assert extract_resolution(str(f), ".mp3") == ""


def test_extract_resolution_square(tmp_path):
    filepath = make_image(tmp_path / "square.png", (512, 512), "PNG")
    assert extract_resolution(filepath, ".png") == "512x512"

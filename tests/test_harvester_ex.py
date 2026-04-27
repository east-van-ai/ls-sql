"""
tests for lssql.harvester_ex -- JPG EXIF metadata extraction.
uses piexif to write real EXIF tags into tmp files.
"""

import piexif
import pytest
from lssql.harvester_ex import build_ex_tag_string, extract_jpg_tags


from PIL import Image
import io


def make_jpg(path):
    """create a valid JPG file using Pillow."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img.save(str(path), format="JPEG")
    return str(path)


def make_jpg_with_exif(path, exif_dict):
    """create a valid JPG with provided EXIF dict."""
    make_jpg(path)
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, str(path))
    return str(path)


def base_exif():
    """return a base EXIF dict with all IFDs."""
    return {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}


# -- extract_jpg_tags --


def test_extract_jpg_tags_dto(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = b"2024:07:12 14:30:00"
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:dto"] == "2024:07:12"


def test_extract_jpg_tags_cam(tmp_path):
    exif = base_exif()
    exif["0th"][piexif.ImageIFD.Model] = b"Canon EOS R5"
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:cam"] == "canon-eos-r5"


def test_extract_jpg_tags_iso(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 400
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:iso"] == "400"


def test_extract_jpg_tags_aperture(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.FNumber] = (28, 10)  # f2.8
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:ap"] == "f2.8"


def test_extract_jpg_tags_focal_length(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.FocalLength] = (50, 1)  # 50mm
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:fl"] == "50mm"


def test_extract_jpg_tags_full(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = b"2024:07:12 14:30:00"
    exif["0th"][piexif.ImageIFD.Model] = b"Sony A7IV"
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 800
    exif["Exif"][piexif.ExifIFD.FNumber] = (14, 5)  # f2.8
    exif["Exif"][piexif.ExifIFD.FocalLength] = (85, 1)
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:dto"] == "2024:07:12"
    assert tags["ex:cam"] == "sony-a7iv"
    assert tags["ex:iso"] == "800"
    assert tags["ex:ap"] == "f2.8"
    assert tags["ex:fl"] == "85mm"


def test_extract_jpg_tags_empty_exif(tmp_path):
    filepath = make_jpg(tmp_path / "photo.jpg")
    tags = extract_jpg_tags(filepath)
    assert tags == {}


def test_extract_jpg_tags_partial(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 200
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:iso"] == "200"
    assert "ex:dto" not in tags
    assert "ex:cam" not in tags


# -- build_ex_tag_string --


def test_build_ex_tag_string_jpg(tmp_path):
    exif = base_exif()
    exif["0th"][piexif.ImageIFD.Model] = b"Fujifilm X-T5"
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 1600
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    result = build_ex_tag_string(filepath, ".jpg")
    assert "ex:cam=fujifilm-x-t5" in result
    assert "ex:iso=1600" in result


def test_build_ex_tag_string_jpeg_extension(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] = 100
    filepath = make_jpg_with_exif(tmp_path / "photo.jpeg", exif)

    result = build_ex_tag_string(filepath, ".jpeg")
    assert "ex:iso=100" in result


def test_build_ex_tag_string_non_jpg(tmp_path):
    f = tmp_path / "photo.png"
    f.write_text("x")
    result = build_ex_tag_string(str(f), ".png")
    assert result == ""


def test_build_ex_tag_string_aperture_formatting(tmp_path):
    exif = base_exif()
    exif["Exif"][piexif.ExifIFD.FNumber] = (4, 1)  # f4 not f4.0
    filepath = make_jpg_with_exif(tmp_path / "photo.jpg", exif)

    tags = extract_jpg_tags(filepath)
    assert tags["ex:ap"] == "f4"

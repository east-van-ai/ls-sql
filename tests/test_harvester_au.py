"""
tests for lssql.harvester_au -- MP3 metadata extraction.
uses mutagen to write real ID3 tags into tmp files.
"""

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from lssql.harvester_au import build_au_tag_string, extract_mp3_tags


def make_mp3(path):
    """create a minimal valid MP3 file with ID3 tags."""
    # minimal MP3 frame header -- silent but valid enough for mutagen
    mp3_bytes = bytes(
        [
            0xFF,
            0xFB,
            0x90,
            0x00,  # MPEG1, Layer3, 128kbps, 44100Hz
        ]
        + [0x00] * 413
    )
    path.write_bytes(mp3_bytes)
    tags = EasyID3()
    tags.save(str(path))
    return str(path)


def test_extract_mp3_tags_full(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["artist"] = ["The Tragically Hip"]
    audio["album"] = ["Road Apples"]
    audio["title"] = ["Little Bones"]
    audio["tracknumber"] = ["1/12"]
    audio["date"] = ["1991"]
    audio.save()

    tags = extract_mp3_tags(filepath)
    assert tags["au:ar"] == "The Tragically Hip"
    assert tags["au:al"] == "Road Apples"
    assert tags["au:tt"] == "Little Bones"
    assert tags["au:tn"] == "1"
    assert tags["au:yr"] == "1991"


def test_extract_mp3_tags_partial(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["artist"] = ["Solo Artist"]
    audio.save()

    tags = extract_mp3_tags(filepath)
    assert tags["au:ar"] == "Solo Artist"
    assert "au:al" not in tags
    assert "au:tt" not in tags


def test_extract_mp3_tags_empty(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    tags = extract_mp3_tags(filepath)
    assert tags == {}


def test_build_au_tag_string_mp3(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["artist"] = ["Tom Petty"]
    audio["title"] = ["I Won't Back Down"]
    audio.save()

    result = build_au_tag_string(filepath, ".mp3")
    assert "au:ar=Tom Petty" in result
    assert "au:tt=I Won't Back Down" in result


def test_build_au_tag_string_non_mp3(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("x")
    result = build_au_tag_string(str(f), ".jpg")
    assert result == ""


def test_build_au_tag_string_tracknumber_strips_total(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["tracknumber"] = ["3/14"]
    audio.save()

    tags = extract_mp3_tags(filepath)
    assert tags["au:tn"] == "3"


def test_build_au_tag_string_year_truncated(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["date"] = ["2026-04-26"]
    audio.save()

    tags = extract_mp3_tags(filepath)
    assert tags["au:yr"] == "2026"

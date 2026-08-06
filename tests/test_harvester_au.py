# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
tests for lssql.harvester_au -- MP3 and M4A metadata extraction.
uses mutagen to write real tags into tmp files.
"""

import shutil
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3

from lssql.harvester_au import _extract_m4a_tags, _extract_mp3_tags, build_au_tag_string


def make_mp3(path):
    """create a minimal valid MP3 file with ID3 tags."""
    # minimal MP3 frame header -- silent but valid enough for mutagen
    mp3_bytes = bytes([0xFF, 0xFB, 0x90, 0x00] + [0x00] * 413)
    path.write_bytes(mp3_bytes)
    tags = EasyID3()
    tags.save(str(path))
    return str(path)


# -- MP3 tests ---------------------------------------------------------------


def test_extract_mp3_tags_full(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["artist"] = ["The Tragically Hip"]
    audio["album"] = ["Road Apples"]
    audio["title"] = ["Little Bones"]
    audio["tracknumber"] = ["1/12"]
    audio["date"] = ["1991"]
    audio.save()

    tags = _extract_mp3_tags(filepath)
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

    tags = _extract_mp3_tags(filepath)
    assert tags["au:ar"] == "Solo Artist"
    assert "au:al" not in tags
    assert "au:tt" not in tags


def test_extract_mp3_tags_empty(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    tags = _extract_mp3_tags(filepath)
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


def test_build_au_tag_string_non_audio(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("x")
    result = build_au_tag_string(str(f), ".jpg")
    assert result == ""


def test_build_au_tag_string_tracknumber_strips_total(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["tracknumber"] = ["3/14"]
    audio.save()

    tags = _extract_mp3_tags(filepath)
    assert tags["au:tn"] == "3"


def test_build_au_tag_string_year_truncated(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["date"] = ["2026-04-26"]
    audio.save()

    tags = _extract_mp3_tags(filepath)
    assert tags["au:yr"] == "2026"


def test_build_au_tag_string_with_carets_semicolons_mp3(tmp_path):
    filepath = make_mp3(tmp_path / "song.mp3")
    audio = EasyID3(filepath)
    audio["artist"] = ["abc^^^def"]
    audio["title"] = ["uvw^xyz;;,;123"]
    audio.save()

    result = build_au_tag_string(filepath, ".mp3")
    assert "au:ar=abc---def" in result
    assert "au:tt=uvw-xyz--,-123" in result


# -- M4A tests ---------------------------------------------------------------


TEST_DATA = Path(__file__).parent / "data"


def make_m4a(path):
    src = TEST_DATA / "sample.m4a"
    if not src.exists():
        pytest.skip("test M4A file not in tests/data/ -- see tests/README.md")
    shutil.copy(src, path)
    return str(path)


def test_extract_m4a_tags_full(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    from mutagen.mp4 import MP4

    audio = MP4(filepath)
    audio["\xa9ART"] = ["Oasis"]
    audio["\xa9alb"] = ["(What's the Story) Morning Glory?"]
    audio["\xa9nam"] = ["Don't Look Back in Anger"]
    audio["\xa9day"] = ["1995"]
    audio["trkn"] = [(5, 0)]
    audio.save()

    tags = _extract_m4a_tags(filepath)
    assert tags["au:ar"] == "Oasis"
    assert tags["au:al"] == "(What's the Story) Morning Glory?"
    assert tags["au:tt"] == "Don't Look Back in Anger"
    assert tags["au:yr"] == "1995"
    assert tags["au:tn"] == "5"


def test_extract_m4a_tags_partial(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    from mutagen.mp4 import MP4

    audio = MP4(filepath)
    audio["\xa9ART"] = ["Group Artist"]
    audio.save()

    tags = _extract_m4a_tags(filepath)
    assert tags["au:ar"] == "Group Artist"
    assert "au:al" not in tags
    assert "au:tt" not in tags


def test_extract_m4a_tags_empty(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    tags = _extract_m4a_tags(filepath)
    assert tags == {}


def test_build_au_tag_string_m4a(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    from mutagen.mp4 import MP4

    audio = MP4(filepath)
    audio["\xa9ART"] = ["Oasis"]
    audio["\xa9nam"] = ["Wonderwall"]
    audio.save()

    result = build_au_tag_string(filepath, ".m4a")
    assert "au:ar=Oasis" in result
    assert "au:tt=Wonderwall" in result


def test_extract_m4a_tags_year_truncated(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    from mutagen.mp4 import MP4

    audio = MP4(filepath)
    audio["\xa9day"] = ["1995-01-01"]
    audio.save()

    tags = _extract_m4a_tags(filepath)
    assert tags["au:yr"] == "1995"


def test_build_au_tag_string_with_carets_semicolons_m4a(tmp_path):
    filepath = make_m4a(tmp_path / "song.m4a")
    from mutagen.mp4 import MP4

    audio = MP4(filepath)
    audio["\xa9ART"] = ["abc^^^def;,;ghi"]
    audio["\xa9nam"] = ["uvw^xyz"]
    audio.save()

    result = build_au_tag_string(filepath, ".m4a")
    assert "au:ar=abc---def-,-ghi" in result
    assert "au:tt=uvw-xyz" in result

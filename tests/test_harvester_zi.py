"""
tests for lssql.harvester_zi -- ZIP metadata extraction.
uses zipfile stdlib to create real ZIP files in tmp_path.
"""

import zipfile
import pytest
from lssql.harvester_zi import build_zi_tag_string, _extract_zip_tags


def make_zip(path, entries: list[tuple[str, bytes]]) -> str:
    """
    create a ZIP file at path with given entries.
    entries is a list of (filename, content) tuples.
    use content=None for directories.
    """
    with zipfile.ZipFile(str(path), "w") as zf:
        for name, content in entries:
            if content is None:
                (
                    zf.mkdir(name)
                    if hasattr(zf, "mkdir")
                    else zf.writestr(zipfile.ZipInfo(name + "/"), "")
                )
            else:
                zf.writestr(name, content)
    return str(path)


# -- zi:cnt ------------------------------------------------------------------


def test_cnt_flat_files(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photo.jpg", b"x"),
            ("doc.pdf", b"x"),
            ("note.txt", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:cnt"] == "3"


# -- zi:ext ------------------------------------------------------------------


def test_ext_sorted_unique(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("a.jpg", b"x"),
            ("b.jpg", b"x"),
            ("c.png", b"x"),
            ("d.txt", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:ext"] == "jpg;png;txt"


def test_ext_excludes_directories(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("folder/", None),  # type: ignore
            ("folder/a.jpg", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert "zi:ext" in tags
    assert tags["zi:ext"] == "jpg"


def test_ext_no_extensions(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("Makefile", b"x"),
            ("LICENSE", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert "zi:ext" not in tags


# -- zi:dot ------------------------------------------------------------------


def test_dot_absent_when_none(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photo.jpg", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert "zi:dot" not in tags


def test_dot_counts_dot_files(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photo.jpg", b"x"),
            (".DS_Store", b"x"),
            (".gitignore", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:dot"] == "2"


def test_dot_counts_dot_directories(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            (".git/", None),  # type: ignore
            ("photo.jpg", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:dot"] == "1"


# -- zi:dir ------------------------------------------------------------------


def test_dir_zero_flat_archive(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photo.jpg", b"x"),
            ("note.txt", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:dir"] == "0"


def test_dir_one_single_wrap(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("folder/", None),  # type: ignore
            ("folder/a.jpg", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert tags["zi:dir"] == "1"


def test_dir_structured_archive(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photos/", None),  # type: ignore
            ("photos/a.jpg", b"x"),
            ("docs/", None),
            ("docs/readme.txt", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert int(tags["zi:dir"]) >= 2


# -- build_zip_tag_string ----------------------------------------------------


def test_build_zip_tag_string_zip(tmp_path):
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photo.jpg", b"x"),
            ("note.txt", b"x"),
        ],
    )
    result = build_zi_tag_string(str(p), ".zip")
    assert "zi:cnt=2" in result
    assert "zi:ext=jpg;txt" in result


def test_build_zip_tag_string_cbz(tmp_path):
    p = make_zip(
        tmp_path / "a.cbz",
        [
            ("photo.jpg", b"x"),
            ("note.txt", b"x"),
        ],
    )
    result = build_zi_tag_string(str(p), ".cbz")
    assert "zi:cnt=2" in result
    assert "zi:ext=jpg;txt" in result


def test_build_zip_tag_string_non_zip(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("x")
    result = build_zi_tag_string(str(f), ".jpg")
    assert result == ""


def test_build_zip_tag_string_empty_zip(tmp_path):
    p = tmp_path / "empty.zip"
    with zipfile.ZipFile(str(p), "w"):
        pass
    result = build_zi_tag_string(str(p), ".zip")
    assert result == ""


# -- implicit directories ----------------------------------------------------


def test_dir_counts_implicit_directories(tmp_path):
    """files only, no explicit directory entries -- implicit dirs still counted."""
    p = make_zip(
        tmp_path / "a.zip",
        [
            ("photos/a.jpg", b"x"),
            ("photos/b.jpg", b"x"),
            ("docs/readme.txt", b"x"),
        ],
    )
    tags = _extract_zip_tags(p)
    assert int(tags["zi:dir"]) == 2  # 'photos' and 'docs'

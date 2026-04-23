"""
tests for lssql.harvester with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
* 'freeze_date' -- a custom pytest fixture defined in 'conftest.py'
"""

import os
import pytest
from unittest.mock import patch
import lssql.harvester as harvester
from lssql.harvester import (
    build_harvested_filename,
    # harvest_date,
    harvest_directory,
    harvest_file,
    is_already_harvested,
    remove_tags_from_directory,
    remove_tags_from_filename,
)

# -- harvest_date --


def test_harvest_date(freeze_date):
    """harvest_date() must be called via the module, not imported directly, while freeze_date is active."""
    assert len(harvester.harvest_date()) == 8
    assert harvester.harvest_date().isdigit()
    assert harvester.harvest_date() == "20260421"


# -- is_already_harvested --


def test_already_harvested_plain_filename():
    assert is_already_harvested("photo.jpg") is False


def test_already_harvested_filename_with_empty_tags():
    assert is_already_harvested("^^^.jpg") is True
    assert is_already_harvested("photo^^^.jpg") is True
    assert is_already_harvested("photo^^^^^^.jpg") is True
    # assert is_already_harvested("photo^^^^^.jpg") is False # 5 carets. must fail


def test_already_harvested_with_separator():
    assert is_already_harvested("photo^^^ls:hd=20260421.jpg") is True
    assert is_already_harvested("photo^^^ls:hd=20260421^^^.jpg") is True
    assert is_already_harvested("photo^^^ls:hd=20260421^^^london.jpg") is True


# -- build_harvested_filename --


def test_build_harvested_filename_simple(freeze_date):
    result = build_harvested_filename("photo.jpg")
    assert result == "photo^^^ls:hd=20260421.jpg"


def test_build_harvested_filename_preserves_original_stem(freeze_date):
    result = build_harvested_filename("00234-1234567890.png")
    assert result == "00234-1234567890^^^ls:hd=20260421.png"


def test_build_harvested_filename_preserves_extension(freeze_date):
    result = build_harvested_filename("song.mp3")
    assert result == "song^^^ls:hd=20260421.mp3"


# -- harvest_file --


def test_harvest_file_dry_run(freeze_date):
    result = harvest_file("/some/dir", "photo.jpg", commit=False)
    assert result["status"] == "dry-run"
    assert result["new_name"] == "photo^^^ls:hd=20260421.jpg"


def test_harvest_file_commit(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    result = harvest_file(str(tmp_path), "photo.jpg", commit=True)

    assert result["status"] == "renamed"
    assert result["new_name"] == "photo^^^ls:hd=20260421.jpg"
    assert (tmp_path / "photo^^^ls:hd=20260421.jpg").exists()
    assert not (tmp_path / "photo.jpg").exists()


def test_harvest_file_skips_already_harvested():
    result = harvest_file("/some/dir", "photo^^^ls:hd=20260420.jpg", commit=False)
    assert result["status"] == "skipped"
    assert result["reason"] == "already harvested"


# -- harvest_directory --


def test_harvest_directory_dry_run(tmp_path, freeze_date):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.png").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    assert all(r["status"] == "dry-run" for r in results)
    assert len(results) == 2
    # no actual renames happened
    assert (tmp_path / "a.jpg").exists()
    assert (tmp_path / "b.png").exists()


def test_harvest_directory_commit(tmp_path, freeze_date):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.png").write_text("x")

    results = harvest_directory(str(tmp_path), commit=True)

    assert all(r["status"] == "renamed" for r in results)
    assert (tmp_path / f"a^^^ls:hd=20260421.jpg").exists()
    assert (tmp_path / f"b^^^ls:hd=20260421.png").exists()


def test_harvest_directory_skips_hidden(tmp_path, freeze_date):
    (tmp_path / ".hidden.jpg").write_text("x")
    (tmp_path / "visible.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert ".hidden.jpg" not in filenames
    assert "visible.jpg" in filenames


def test_harvest_directory_skips_no_extension(tmp_path, freeze_date):
    (tmp_path / "noext").write_text("x")
    (tmp_path / "hasext.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert "noext" not in filenames
    assert "hasext.jpg" in filenames


def test_harvest_directory_skips_already_harvested(tmp_path, freeze_date):
    (tmp_path / "photo^^^ls:hd=20260420.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    assert results[0]["status"] == "skipped"


def test_harvest_directory_recursive(tmp_path, freeze_date):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.jpg").write_text("x")
    (sub / "nested.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, recursive=True)

    filenames = [r["file"] for r in results]
    assert "top.jpg" in filenames
    assert "nested.jpg" in filenames


def test_harvest_directory_not_recursive_by_default(tmp_path, freeze_date):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.jpg").write_text("x")
    (sub / "nested.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert "top.jpg" in filenames
    assert "nested.jpg" not in filenames


# -- remove_tags_from_filename --


def test_remove_tags_from_filename_simple(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260421.jpg")
    assert result == "photo.jpg"


def test_remove_tags_from_filename_simple_no_comment(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260421^^^.jpg")
    assert result == "photo.jpg"


def test_remove_tags_from_filename_preserves_comment(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260421^^^nice-day.jpg")
    assert result == "photo^^^^^^nice-day.jpg"


def test_remove_tags_from_filename_multiple_tags(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260421^ud:test=hello.jpg")
    assert result == "photo.jpg"


# -- remove_tags_from_directory --


def test_remove_tags_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo^^^ls:hd=20260421.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    assert results[0]["status"] == "dry-run"
    assert results[0]["new_name"] == "photo.jpg"
    assert (tmp_path / "photo^^^ls:hd=20260421.jpg").exists()


def test_remove_tags_commit(tmp_path, freeze_date):
    (tmp_path / "photo^^^ls:hd=20260421.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=True)

    assert results[0]["status"] == "restored"
    assert (tmp_path / "photo.jpg").exists()
    assert not (tmp_path / "photo^^^ls:hd=20260421.jpg").exists()


def test_remove_tags_skips_unharvested(tmp_path):
    (tmp_path / "photo.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    assert results[0]["status"] == "skipped"
    assert results[0]["reason"] == "not harvested"


def test_remove_tags_skips_hidden(tmp_path):
    (tmp_path / ".hidden^^^ls:hd=20260421.jpg").write_text("x")
    (tmp_path / "visible^^^ls:hd=20260421.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert ".hidden^^^ls:hd=20260421.jpg" not in filenames
    assert "visible^^^ls:hd=20260421.jpg" in filenames


def test_remove_tags_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top^^^ls:hd=20260421.jpg").write_text("x")
    (sub / "nested^^^ls:hd=20260421.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False, recursive=True)

    filenames = [r["file"] for r in results]
    assert "top^^^ls:hd=20260421.jpg" in filenames
    assert "nested^^^ls:hd=20260421.jpg" in filenames


def test_remove_tags_not_recursive_by_default(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top^^^ls:hd=20260421.jpg").write_text("x")
    (sub / "nested^^^ls:hd=20260421.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert "top^^^ls:hd=20260421.jpg" in filenames
    assert "nested^^^ls:hd=20260421.jpg" not in filenames

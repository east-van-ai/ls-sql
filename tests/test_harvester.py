"""
tests for lssql.harvester with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
* 'freeze_date' -- a custom pytest fixture defined in 'conftest.py'
"""

import pytest
from lssql.harvester import (
    build_harvested_filename,
    harvest_directory,
    harvest_file,
    is_already_harvested,
    is_troublesome_name,
    remove_tags_from_directory,
    remove_tags_from_filename,
)

# -- is_troublesome_name --


def test_is_troublesome_name():
    assert is_troublesome_name("photo^^^hello^^^hey^^^you.jpg") is True
    assert is_troublesome_name("photo^^^hello^^^hey^^^you^^^.jpg") is True


# -- is_already_harvested --


def test_already_harvested_plain_filename():
    assert is_already_harvested("photo.jpg") is False


def _caret_filenames(max_carets: int = 15, prefix: str = ""):
    """
    Yield filenames of the form ``<prefix><caret‑string>.jpg``.

    * ``max_carets`` – maximum number of ^ characters (inclusive).
    * ``prefix``    – optional string that appears before the carets.
    """
    for n in range(1, max_carets + 1):
        yield f"{prefix}{'^' * n}.jpg"


@pytest.mark.parametrize("filename", _caret_filenames(prefix=""))
def test_carets_only_without_prefix_without_postfix(filename):
    """A caret‑only filename must be reported as *not* harvested."""
    assert is_already_harvested("^^^.jpg") is False
    assert not is_already_harvested(filename)


@pytest.mark.parametrize("filename", _caret_filenames(prefix="img_"))
def test_carets_only_with_prefix_without_postfix(filename):
    """A prefixed caret‑only filename must be reported as *not* harvested."""
    assert is_already_harvested("img_^^^.jpg") is False
    assert not is_already_harvested(filename)


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


## -- build_harvested_filename with ls:fh --


def test_build_harvested_filename_includes_fh(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = build_harvested_filename("photo.jpg", str(tmp_path))
    assert "ls:hd=20260421" in result
    assert "ls:fh=" in result


def test_build_harvested_filename_fh_is_10_chars(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = build_harvested_filename("photo.jpg", str(tmp_path))
    # extract fh value
    fh_part = [p for p in result.split("^") if p.startswith("ls:fh=")][0]
    fh_value = fh_part.split("=")[1].split("^")[0].split("^")[0]
    # strip extension if it crept in
    fh_value = fh_value.split(".")[0]
    assert len(fh_value) == 10


# -- harvest_file --


def test_harvest_file_dry_run(tmp_path, freeze_date):
    some = tmp_path / "some"
    some.mkdir()
    f = some / "photo.jpg"
    f.write_text("fake image content")
    result = harvest_file(str(some), "photo.jpg", commit=False)
    assert result["status"] == "dry-run"
    assert result["new_name"] == "photo^^^ls:hd=20260421^ls:fh=03754271b0.jpg"


def test_harvest_file_commit(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    result = harvest_file(str(tmp_path), "photo.jpg", commit=True)

    assert result["status"] == "renamed"
    assert result["new_name"] == "photo^^^ls:hd=20260421^ls:fh=03754271b0.jpg"
    assert (tmp_path / "photo^^^ls:hd=20260421^ls:fh=03754271b0.jpg").exists()
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
    (tmp_path / "a.jpg").write_text("fake image content")
    (tmp_path / "b.png").write_text("fake image content")

    results = harvest_directory(str(tmp_path), commit=True)

    assert all(r["status"] == "renamed" for r in results)
    assert (tmp_path / f"a^^^ls:hd=20260421^ls:fh=03754271b0.jpg").exists()
    assert (tmp_path / f"b^^^ls:hd=20260421^ls:fh=03754271b0.png").exists()


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


# -- harvest_directory -- max_files --
"""
os.scandir, which is used in 'harvest_directory', doesn't guarantee 
alphabetical order, so these tests only assert on count, not which specific 
files get picked. That's the right call. If deterministic file selection is
needed with --max, that's a separate design decision.
"""


def test_harvest_directory_max_files_limits_results(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpg").write_text("x")
    (tmp_path / "c.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, max_files=2)

    assert len(results) == 2


def test_harvest_directory_max_files_zero_means_no_limit(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpg").write_text("x")
    (tmp_path / "c.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, max_files=0)

    assert len(results) == 3


def test_harvest_directory_max_files_larger_than_available(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, max_files=10)

    assert len(results) == 2


def test_harvest_directory_max_files_less_than_zero_means_no_harvest(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, max_files=-5)

    assert len(results) == 0


def test_harvest_directory_max_files_one(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.jpg").write_text("x")
    (tmp_path / "c.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, max_files=1)

    assert len(results) == 1


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

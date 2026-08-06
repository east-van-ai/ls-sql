# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
tests for lssql.harvester with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
* 'freeze_date' -- a custom pytest fixture defined in 'conftest.py'
"""

from lssql.harvester import (
    build_harvested_filename,
    harvest_directory,
    harvest_file,
    remove_tags_from_directory,
    remove_tags_from_filename,
    verify_directory,
    verify_file,
)
from lssql.harvester_ls import content_hash

# -- build_harvested_filename --


def test_build_harvested_filename_simple(freeze_date):
    result = build_harvested_filename("photo.jpg")
    assert result == "photo^^^ls:hd=20260503^^^.jpg"


def test_build_harvested_filename_preserves_original_stem(freeze_date):
    result = build_harvested_filename("00234-1234567890.png")
    assert result == "00234-1234567890^^^ls:hd=20260503^^^.png"


def test_build_harvested_filename_preserves_extension(freeze_date):
    result = build_harvested_filename("song.mp3")
    assert result == "song^^^ls:hd=20260503^^^.mp3"


# -- build_harvested_filename with ls:fh --


def test_build_harvested_filename_includes_fh(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = build_harvested_filename("photo.jpg", str(tmp_path))
    assert "ls:hd=20260503" in result
    assert "ls:fh=" in result


def test_build_harvested_filename_fh_is_16_chars(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = build_harvested_filename("photo.jpg", str(tmp_path))
    # extract fh value
    fh_part = next(p for p in result.split("^") if p.startswith("ls:fh="))
    fh_value = fh_part.split("=")[1].split("^")[0].split("^")[0]
    # strip extension if it crept in
    fh_value = fh_value.split(".")[0]
    assert len(fh_value) == 16


# -- harvest_file --


def test_harvest_file_dry_run(tmp_path, freeze_date):
    some = tmp_path / "some"
    some.mkdir()
    f = some / "photo.jpg"
    f.write_text("fake image content")
    result = harvest_file(str(some), "photo.jpg", commit=False)
    assert result["status"] == "dry-run"
    assert result["new_name"] == "photo^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^^^.jpg"


def test_harvest_file_commit(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    result = harvest_file(str(tmp_path), "photo.jpg", commit=True)

    assert result["status"] == "renamed"
    assert result["new_name"] == "photo^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^^^.jpg"
    assert (tmp_path / "photo^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^^^.jpg").exists()
    assert not (tmp_path / "photo.jpg").exists()


def test_harvest_file_skips_already_harvested():
    result = harvest_file("/some/dir", "photo^^^ls:hd=20260420.jpg", commit=False)
    assert result["status"] == "skipped"
    assert result["reason"] == "already harvested"


def test_harvest_file_skips_caret_file():
    result = harvest_file("/some/dir", "photo^from^france.jpg", commit=False)
    assert result["status"] == "skipped"
    assert "caret" in result["reason"]


def test_harvest_file_skips_long_filename():
    long_filename = "photo-paris-france-" * 5 + ".jpg"  # 19 * 5 = 95
    result = harvest_file("/some/dir", long_filename, commit=False)
    assert result["status"] == "skipped"
    assert "filename" in result["reason"]
    assert "95" in result["reason"]


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
    assert (tmp_path / "a^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^^^.jpg").exists()
    assert (tmp_path / "b^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^^^.png").exists()


def test_harvest_directory_skips_hidden(tmp_path, freeze_date):
    (tmp_path / ".hidden.jpg").write_text("x")
    (tmp_path / "visible.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert ".hidden.jpg" not in filenames
    assert "visible.jpg" in filenames


def test_harvest_directory_skips_no_extension(tmp_path, freeze_date):
    (tmp_path / "no-ext").write_text("x")
    (tmp_path / "has-ext.jpg").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert "no-ext" not in filenames
    assert "has-ext.jpg" in filenames


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


# -- harvest_directory with --ext --


def test_harvest_directory_ext_filter_includes(tmp_path, freeze_date):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.png").write_text("x")
    (tmp_path / "c.mp3").write_text("x")

    results = harvest_directory(
        str(tmp_path), commit=False, allowed_exts={".jpg", ".png"}
    )

    filenames = [r["file"] for r in results if r["status"] == "dry-run"]
    assert "a.jpg" in filenames
    assert "b.png" in filenames
    assert "c.mp3" not in filenames


def test_harvest_directory_ext_filter_skips_with_reason(tmp_path, freeze_date):
    (tmp_path / "a.mp3").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, allowed_exts={".jpg"})

    assert results[0]["status"] == "skipped"
    assert results[0]["reason"] == "extension not in whitelist or --ext list"


def test_harvest_directory_no_ext_filter_accepts_all(tmp_path, freeze_date):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.mp3").write_text("x")
    (tmp_path / "c.zip").write_text("x")

    results = harvest_directory(str(tmp_path), commit=False, allowed_exts=set())

    assert all(r["status"] == "dry-run" for r in results)
    assert len(results) == 3


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
    result = remove_tags_from_filename("photo^^^ls:hd=20260503.jpg")
    assert result == "photo.jpg"


def test_remove_tags_from_filename_simple_no_comment(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260503^^^.jpg")
    assert result == "photo.jpg"


def test_remove_tags_from_filename_preserves_comment(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260503^^^nice-day.jpg")
    assert result == "photo^^^^^^nice-day.jpg"


def test_remove_tags_from_filename_multiple_tags(freeze_date):
    result = remove_tags_from_filename("photo^^^ls:hd=20260503^ud:test=hello.jpg")
    assert result == "photo.jpg"


# -- remove_tags_from_directory --


def test_remove_tags_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo^^^ls:hd=20260503.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    assert results[0]["status"] == "dry-run"
    assert results[0]["new_name"] == "photo.jpg"
    assert (tmp_path / "photo^^^ls:hd=20260503.jpg").exists()


def test_remove_tags_commit(tmp_path, freeze_date):
    (tmp_path / "photo^^^ls:hd=20260503.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=True)

    assert results[0]["status"] == "restored"
    assert (tmp_path / "photo.jpg").exists()
    assert not (tmp_path / "photo^^^ls:hd=20260503.jpg").exists()


def test_remove_tags_skips_unharvested(tmp_path):
    (tmp_path / "photo.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    assert results[0]["status"] == "skipped"
    assert results[0]["reason"] == "not harvested"


def test_remove_tags_skips_hidden(tmp_path):
    (tmp_path / ".hidden^^^ls:hd=20260503.jpg").write_text("x")
    (tmp_path / "visible^^^ls:hd=20260503.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert ".hidden^^^ls:hd=20260503.jpg" not in filenames
    assert "visible^^^ls:hd=20260503.jpg" in filenames


def test_remove_tags_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top^^^ls:hd=20260503.jpg").write_text("x")
    (sub / "nested^^^ls:hd=20260503.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False, recursive=True)

    filenames = [r["file"] for r in results]
    assert "top^^^ls:hd=20260503.jpg" in filenames
    assert "nested^^^ls:hd=20260503.jpg" in filenames


def test_remove_tags_not_recursive_by_default(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top^^^ls:hd=20260503.jpg").write_text("x")
    (sub / "nested^^^ls:hd=20260503.jpg").write_text("x")

    results = remove_tags_from_directory(str(tmp_path), commit=False)

    filenames = [r["file"] for r in results]
    assert "top^^^ls:hd=20260503.jpg" in filenames
    assert "nested^^^ls:hd=20260503.jpg" not in filenames


def test_verify_file_ok(tmp_path):
    """file hash matches -- status ok."""

    f = tmp_path / "photo.jpg"
    f.write_bytes(b"hello")
    fh = content_hash(str(f))
    harvested = f"photo^^^ls:hd=20260501^ls:fh={fh}^^^.jpg"
    (tmp_path / harvested).write_bytes(b"hello")

    result = verify_file(str(tmp_path), harvested)
    assert result["status"] == "ok"


def test_verify_file_changed(tmp_path):
    """file content changed -- status changed."""

    harvested = "photo^^^ls:hd=20260501^ls:fh=1234567890123456^^^.jpg"
    f = tmp_path / harvested
    f.write_bytes(b"hello")

    result = verify_file(str(tmp_path), harvested)
    assert result["status"] == "changed"
    assert result["stored"] == "1234567890123456"
    assert result["actual"] != "1234567890123456"


def test_verify_file_not_harvested(tmp_path):
    """plain filename -- skipped, no ls:fh."""

    f = tmp_path / "photo.jpg"
    f.write_bytes(b"hello")

    result = verify_file(str(tmp_path), "photo.jpg")
    assert result["status"] == "skipped"
    assert "harvest first" in result["reason"]


def test_verify_file_no_fh_tag(tmp_path):
    """harvested but no ls:fh tag -- skipped."""

    filename = "photo^^^ls:hd=20260501^^^.jpg"
    (tmp_path / filename).write_bytes(b"hello")

    result = verify_file(str(tmp_path), filename)
    assert result["status"] == "skipped"
    assert "harvest first" in result["reason"]


def test_verify_directory(tmp_path):
    """verify_directory returns results for all files."""

    f = tmp_path / "photo^^^ls:hd=20260501^ls:fh=1234567890123456^^^.jpg"
    f.write_bytes(b"hello")

    results = verify_directory(str(tmp_path))
    assert any(r["status"] == "changed" for r in results)

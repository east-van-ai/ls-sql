"""
round-trip integration tests for lssql.harvester.
harvest then remove-all-tags must equal the original filename.
* 'tmp_path'    -- built-in pytest fixture. fresh temporary directory per test.
* 'freeze_date' -- custom fixture in conftest.py. deterministic harvest date.
"""

from lssql.harvester import harvest_directory, harvest_file, remove_tags_from_directory

# -- harvest then remove-all-tags --


def test_round_trip_plain_file(tmp_path, freeze_date):
    """plain file: harvest then remove returns original filename."""
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    harvest_file(str(tmp_path), "photo.jpg", commit=True)
    remove_tags_from_directory(str(tmp_path), commit=True)

    assert (tmp_path / "photo.jpg").exists()


def test_round_trip_does_not_leave_harvested_file(tmp_path, freeze_date):
    """after remove, no harvested filename remains on disk."""
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    result = harvest_file(str(tmp_path), "photo.jpg", commit=True)
    harvested_name = result["new_name"]
    remove_tags_from_directory(str(tmp_path), commit=True)

    assert not (tmp_path / harvested_name).exists()


def test_round_trip_recursive(tmp_path, freeze_date):
    """recursive: files in subdirectory also round-trip cleanly."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.jpg").write_text("fake image content")
    (sub / "nested.jpg").write_text("fake image content")

    harvest_directory(str(tmp_path), commit=True, recursive=True)
    remove_tags_from_directory(str(tmp_path), commit=True, recursive=True)

    assert (tmp_path / "top.jpg").exists()
    assert (sub / "nested.jpg").exists()


# -- verify --


def test_verify_after_harvest_is_ok(tmp_path, freeze_date):
    """freshly harvested file verifies clean."""
    from lssql.harvester import verify_directory

    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    result = harvest_file(str(tmp_path), "photo.jpg", commit=True)
    harvested_name = result["new_name"]

    results = verify_directory(str(tmp_path))

    assert results[0]["status"] == "ok"


def test_verify_after_content_change_is_changed(tmp_path, freeze_date):
    """file modified after harvest reports changed on verify."""
    from lssql.harvester import verify_directory

    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")

    harvest_file(str(tmp_path), "photo.jpg", commit=True)

    # modify the file content after harvesting
    harvested = list(tmp_path.glob("photo^^^*"))[0]
    harvested.write_text("tampered content")

    results = verify_directory(str(tmp_path))

    assert results[0]["status"] == "changed"

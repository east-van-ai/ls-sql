"""
tests for lssql.scanner with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
"""

from lssql.scanner import scan_directory


class TestScanDirectory:
    def test_returns_list(self, tmp_path):
        result = scan_directory(str(tmp_path))
        assert isinstance(result, list)

    def test_empty_directory_returns_empty_list(self, tmp_path):
        result = scan_directory(str(tmp_path))
        assert result == []

    def test_returns_dict_instances(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        result = scan_directory(str(tmp_path))
        assert all(isinstance(row, dict) for row in result)

    def test_skips_subdirectories(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        result = scan_directory(str(tmp_path))
        assert result == []

    def test_skips_unsupported_files(self, tmp_path):
        (tmp_path / ".notes").write_bytes(b"- fake -")
        (tmp_path / ".archive").write_bytes(b"- fake -")
        result = scan_directory(str(tmp_path))
        assert result == []

    def test_supported_files_are_included(self, tmp_path):
        (tmp_path / "a.jpg").write_bytes(b"- fake -")
        (tmp_path / "b.png").write_bytes(b"- fake -")
        (tmp_path / "c.mp3").write_bytes(b"- fake -")
        result = scan_directory(str(tmp_path))
        assert len(result) == 3

    def test_dict_has_expected_fields(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        row = scan_directory(str(tmp_path))[0]
        assert "path" in row
        assert "original" in row
        assert "tags" in row
        assert "comment" in row
        assert "ext" in row
        assert "harvested" in row

    def test_parsed_field_is_populated(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        row = scan_directory(str(tmp_path))[0]
        assert isinstance(row, dict)
        assert row["path"], "path is not empty"
        assert row["original"], "original(filename) is not empty"
        assert row["tags"] == {}, "tags dict is empty hence not harvested"
        assert row["comment"] == "", "comment is empty hence not harvested"
        assert row["ext"], "file extension is not empty"
        assert row["harvested"] is False, "data is not harvested from 'photo.jpg'"

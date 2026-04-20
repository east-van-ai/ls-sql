"""
tests for lssql.scanner with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
"""

from lssql.scanner import scan_directory, FileRow


class TestScanDirectory:
    def test_returns_list(self, tmp_path):
        result = scan_directory(str(tmp_path))
        assert isinstance(result, list)

    def test_empty_directory_returns_empty_list(self, tmp_path):
        result = scan_directory(str(tmp_path))
        assert result == []

    def test_returns_filerow_instances(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        result = scan_directory(str(tmp_path))
        assert all(isinstance(row, FileRow) for row in result)

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

    def test_filerow_has_expected_fields(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        row = scan_directory(str(tmp_path))[0]
        assert hasattr(row, "path")
        assert hasattr(row, "size")
        assert hasattr(row, "mtime")
        assert hasattr(row, "parsed")

    def test_filerow_repr_is_readable(self, tmp_path):
        # placeholder -- repr format will be revised when __repr__ is overridden
        (tmp_path / "photo.jpg").write_bytes(b"fake")
        row = scan_directory(str(tmp_path))[0]
        result = repr(row)
        assert "FileRow" in result
        assert "path" in result
        assert "size" in result
        assert "parsed" in result

    def test_parsed_field_is_populated(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"- fake -")
        row = scan_directory(str(tmp_path))[0]
        assert isinstance(row.parsed, dict)
        assert "original" in row.parsed

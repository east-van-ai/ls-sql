"""
CLI tests for lssql.
two approaches, both demonstrated intentionally:

  Option A -- subprocess: spawns the real CLI as a child process.
              tests exactly what the user sees. slow but real.
              freeze_date does NOT apply -- subprocess is a separate process,
              patch never reaches it. assert on behaviour, not dates.
              requires --capture=sys in pyproject.toml to prevent pytest's
              fd-level capturing from stealing subprocess stdout.

  Option B -- main() direct: calls main() with mocked sys.argv.
              faster, same argparse and run mode logic, no child process.
              freeze_date applies -- same process, patch works fine.
              sys.stdin.isatty must be patched to True -- pytest's capturing
              makes isatty() return False, which triggers piped mode in cli.py.
              sys.stdout patched with StringIO to capture print() output.
"""

from io import StringIO
import subprocess
import sys
from unittest.mock import patch

import pytest

from lssql.cli import main

# -- Option A: subprocess --


def test_cli_harvest_dry_run_subprocess(tmp_path):
    """subprocess: --harvest without --commit prints dry-run summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        ["ls-sql", "--harvest", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout
    assert "no files changed" in result.stdout


def test_cli_harvest_commit_subprocess(tmp_path):
    """subprocess: --harvest --commit renames file and prints committed summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        ["ls-sql", "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "committed" in result.stdout
    assert len(list(tmp_path.glob("photo^^^*"))) == 1


def test_cli_verify_exit_code_zero_subprocess(tmp_path):
    """subprocess: --verify exits 0 when all files ok."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        ["ls-sql", "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
    )

    result = subprocess.run(
        ["ls-sql", "--verify", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_cli_verify_exit_code_one_subprocess(tmp_path):
    """subprocess: --verify exits 1 when a file has changed."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        ["ls-sql", "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
    )

    harvested = list(tmp_path.glob("photo^^^*"))[0]
    harvested.write_text("tampered content")

    result = subprocess.run(
        ["ls-sql", "--verify", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1


def test_cli_no_path_subprocess():
    """subprocess: missing path prints error and exits 1."""
    result = subprocess.run(
        ["ls-sql", "--harvest"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "error" in result.stdout


# -- Option B: main() direct --


def test_cli_harvest_dry_run_main(tmp_path, freeze_date):
    """main(): --harvest without --commit prints dry-run summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch("sys.argv", ["ls-sql", "--harvest", str(tmp_path)]):
                main()
            assert "dry-run" in mock_out.getvalue()
            assert "no files changed" in mock_out.getvalue()


def test_cli_harvest_commit_main(tmp_path, freeze_date):
    """main(): --harvest --commit renames file and prints committed summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]):
                main()
            assert "committed" in mock_out.getvalue()
        assert len(list(tmp_path.glob("photo^^^*"))) == 1


def test_cli_remove_all_tags_main(tmp_path, freeze_date):
    """main(): --remove-all-tags restores original filename."""
    (tmp_path / "photo^^^ls:hd=20260503^^^.jpg").write_text("fake image content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv", ["ls-sql", "--remove-all-tags", "--commit", str(tmp_path)]
            ):
                main()
            assert "committed" in mock_out.getvalue()
        assert (tmp_path / "photo.jpg").exists()


def test_cli_verify_ok_main(tmp_path, freeze_date):
    """main(): --verify exits 0 when all files ok."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]):
                main()

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--verify", str(tmp_path)]):
                with pytest.raises(SystemExit) as exc:
                    main()

    assert exc.value.code == 0


def test_cli_verify_changed_main(tmp_path, freeze_date):
    """main(): --verify exits 1 when a file has changed."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]):
                main()

    harvested = list(tmp_path.glob("photo^^^*"))[0]
    harvested.write_text("tampered content")

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--verify", str(tmp_path)]):
                with pytest.raises(SystemExit) as exc:
                    main()

    assert exc.value.code == 1


def test_cli_no_path_main():
    """main(): missing path prints error and exits 1."""
    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--harvest"]):
                with pytest.raises(SystemExit) as exc:
                    main()

    assert exc.value.code == 1

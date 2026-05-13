"""
CLI tests for lssql.
two approaches, both demonstrated intentionally:

  Option A -- subprocess: spawns the real CLI as a child process.
              tests exactly what the user sees. slow but real.
              freeze_date does NOT apply -- subprocess is a separate process,
              patch never reaches it. assert on behaviour, not dates.
              skipped in CI -- subprocess stdout capture is unreliable on
              Linux GitHub runners. run locally only.

  Option B -- main() direct: calls main() with mocked sys.argv.
              faster, same argparse and run mode logic, no child process.
              freeze_date applies -- same process, patch works fine.
              sys.stdin.isatty must be patched to True -- pytest's capturing
              makes isatty() return False, which triggers piped mode in cli.py.
              sys.stdout patched with StringIO to capture print() output.
              this is the CI-safe approach. all Option B tests run in CI.
"""

import subprocess
from io import StringIO
from unittest.mock import patch

import pytest

from lssql.cli import main
from tests.test_cli import _ls_sql_bin, skip_on_ci

# -- Option A: subprocess --


@skip_on_ci
def test_cli_harvest_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: --harvest with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


@skip_on_ci
def test_cli_harvest_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: --harvest with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path / "photo.jpg")],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


# -- Option B: main() direct --


def test_cli_harvest_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """
    main(): --harvest with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


def test_cli_harvest_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """
    main(): --harvest with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path / "photo.jpg")]
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


# -- hidden files --


def test_cli_harvest_mode_option_b_directory_containing_hidden_files(
    tmp_path, freeze_date
):
    """
    main(): --harvest mode correctly processes filenames starting with a period (hidden files).
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    (tmp_path / ".hidden-image.jpg").write_text("fake hidden image content")
    (tmp_path / ".hidden-file").write_text("fake content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert not (tmp_path / "photo.jpg").exists()  # renamed by harvester
    assert (tmp_path / ".hidden-image.jpg").exists()
    assert (tmp_path / ".hidden-file").exists()
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


def test_cli_harvest_mode_option_b_hidden_filename(tmp_path, freeze_date):
    """
    main(): --harvest mode correctly processes a filename starting with a period (hidden file)
    """
    (tmp_path / ".photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--harvest", "--commit", str(tmp_path / ".photo.jpg")],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert (tmp_path / ".photo.jpg").exists()

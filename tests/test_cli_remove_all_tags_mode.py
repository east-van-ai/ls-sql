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
def test_cli_remove_all_tags_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: --remove-all-tags with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    result = subprocess.run(
        [_ls_sql_bin(), "--remove-all-tags", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (tmp_path / "photo.jpg").exists()
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_remove_all_tags_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: --remove-all-tags with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    result = subprocess.run(
        [_ls_sql_bin(), "--remove-all-tags", "--commit", str(marked)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (tmp_path / "photo.jpg").exists()
    assert "1 file(s) committed, 0 skipped" in result.stdout


# -- Option B: main() direct --


def test_cli_remove_all_tags_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """
    main(): --remove-all-tags with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit),
    ):
        main()

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--remove-all-tags", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert (tmp_path / "photo.jpg").exists()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_remove_all_tags_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """
    main(): --remove-all-tags with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit),
    ):
        main()

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--remove-all-tags", "--commit", str(marked)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert (tmp_path / "photo.jpg").exists()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

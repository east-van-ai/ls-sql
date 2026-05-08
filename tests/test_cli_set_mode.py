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
def test_cli_set_mode_option_a(tmp_path):
    """
    subprocess: --set with 4 operations
        =   overwrite
        +=  append
        -=  remove
        ==  delete
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
    )

    # implicit dry-run

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=blue;green",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout

    # explicit dry-run

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=blue;green",
            "--dry-run",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout

    # = overwrite operation

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=green;blue",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;green" in result.stdout  # alphabetical order
    assert "1 file(s) committed, 0 skipped" in result.stdout

    # += append operation

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour+=red;blue;blue;green",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;green;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout

    # -= remove operation

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour-=green",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout

    # == delete operation

    result = subprocess.run(
        [_ls_sql_bin(), "--set", "my-custom-tag:colour==", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" not in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


# -- Option B: main() direct --


def test_cli_set_mode_option_b(tmp_path, freeze_date):
    """
    subprocess: --set with 4 operations
        =   overwrite
        +=  append
        -=  remove
        ==  delete
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    assert (tmp_path / "photo.jpg").exists()

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]):
                main()
        assert not (tmp_path / "photo.jpg").exists()
        assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO):
            with patch("sys.argv", ["ls-sql", "--set", str(tmp_path)]):
                with pytest.raises(SystemExit) as exc:
                    main()
    assert exc.value.code == 1

    # implicit dry-run

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                ["ls-sql", "--set", "my-custom-tag:colour=green;blue", str(tmp_path)],
            ):
                main()
            assert "dry-run" in mock_out.getvalue()
            assert "no files changed -- pass --commit to execute" in mock_out.getvalue()

    # explicit dry-run

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                [
                    "ls-sql",
                    "--set",
                    "my-custom-tag:colour=green;blue",
                    "--dry-run",
                    str(tmp_path),
                ],
            ):
                main()
            assert "dry-run" in mock_out.getvalue()
            assert "no files changed -- pass --commit to execute" in mock_out.getvalue()

    # = overwrite operation

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                [
                    "ls-sql",
                    "--set",
                    "my-custom-tag:colour=green;blue",
                    "--commit",
                    str(tmp_path),
                ],
            ):
                main()
            assert "dry-run" not in mock_out.getvalue()
            assert (
                "my-custom-tag:colour=blue;green" in mock_out.getvalue()
            )  # alphabetical order
            assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

    # += append operation

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                [
                    "ls-sql",
                    "--set",
                    "my-custom-tag:colour+=red;blue;blue;green",
                    "--commit",
                    str(tmp_path),
                ],
            ):
                main()
            assert "my-custom-tag:colour=blue;green;red" in mock_out.getvalue()
            assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

    # -= remove operation

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                [
                    "ls-sql",
                    "--set",
                    "my-custom-tag:colour-=green",
                    "--commit",
                    str(tmp_path),
                ],
            ):
                main()
            assert "my-custom-tag:colour=blue;red" in mock_out.getvalue()
            assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

    # == delete operation

    with patch("sys.stdin.isatty", return_value=True):
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            with patch(
                "sys.argv",
                [
                    "ls-sql",
                    "--set",
                    "my-custom-tag:colour==",
                    "--commit",
                    str(tmp_path),
                ],
            ):
                main()
            assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

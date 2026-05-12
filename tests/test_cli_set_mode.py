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
def test_cli_set_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: --set with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    assert (tmp_path / "photo.jpg").exists()

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

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in result.stdout
    assert "my-custom-tag:colour=blue;green" in str(marked)


@skip_on_ci
def test_cli_set_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: --set with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    assert (tmp_path / "photo.jpg").exists()

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=green;blue",
            "--commit",
            str(tmp_path / "photo.jpg"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in result.stdout
    assert "my-custom-tag:colour=blue;green" in str(marked)


@skip_on_ci
def test_cli_set_mode_option_a_no_set_arg(tmp_path):
    """subprocess: --set arg does not exist"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "--set", "--commit", str(tmp_path)],
        capture_output=True,
    )

    assert result.returncode == 2


@skip_on_ci
def test_cli_set_mode_option_a_implicit_dry_run(tmp_path):
    """subprocess: implicit dry-run"""
    (tmp_path / "photo.jpg").write_text("fake image content")

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


@skip_on_ci
def test_cli_set_mode_option_a_explicit_dry_run(tmp_path):
    """subprocess: explicit dry-run"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=blue;green",
            "--dry-run",  # explicit dry-run
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_overwrite_operation(tmp_path):
    """subprocess: --set with = overwrite operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=red",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=green;blue",  # = overwrite operation
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;green" in result.stdout  # alphabetical order
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_append_operation(tmp_path):
    """subprocess: --set with += append"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=red;green",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour+=red;blue;blue;green",  # += append operation
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;green;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_remove_operation(tmp_path):
    """subprocess: --set with -= remove operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour=red;green;blue",
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "--set",
            "my-custom-tag:colour-=green",  # -= remove operation
            "--commit",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "my-custom-tag:colour=blue;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_delete_operation(tmp_path):
    """subprocess: --set with == delete operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
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

    result = subprocess.run(
        [_ls_sql_bin(), "--set", "my-custom-tag:colour==", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" not in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


# -- Option B: main() direct --


def test_cli_set_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """main(): --set with a directory as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=green;blue",
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in str(marked)


def test_cli_set_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """main(): --set with a filename as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=green;blue",
                "--commit",
                str(tmp_path / "photo.jpg"),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in str(marked)


def test_cli_set_mode_option_b_no_set_arg(tmp_path, freeze_date):
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "--set", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1


def test_cli_set_mode_option_b_implicit_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--set", "my-custom-tag:colour=green;blue", str(tmp_path)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed -- pass --commit to execute" in mock_out.getvalue()


def test_cli_set_mode_option_b_explicit_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=green;blue",
                "--dry-run",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed -- pass --commit to execute" in mock_out.getvalue()


def test_cli_set_mode_option_b_overwrite(tmp_path, freeze_date):
    """subprocess: --set with = overwrite operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=green;blue",  # = overwrite operation
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "dry-run" not in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_append(tmp_path, freeze_date):
    """subprocess: --set with += append operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=blue",
                "--commit",
                str(tmp_path / "photo.jpg"),
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour+=red;blue;blue;green",  # += append operation
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "my-custom-tag:colour=blue;green;red" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_remove(tmp_path, freeze_date):
    """subprocess: --set with -= remove operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=blue;green;red",
                "--commit",
                str(tmp_path / "photo.jpg"),
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour-=green",  # -= remove operation
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "my-custom-tag:colour=blue;red" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_delete(tmp_path, freeze_date):
    """subprocess: --set with == delete operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=blue;green;red",
                "--commit",
                str(tmp_path / "photo.jpg"),
            ],
        ),
        pytest.raises(SystemExit),
    ):
        main()

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour==",  # == delete operation
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()

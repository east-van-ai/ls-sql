# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

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
              no stdin patching needed -- cli.stdin_has_content() classifies
              stdin by file type, and pytest's captured stdin has no usable
              fileno(), so piped mode stays off by itself.
              sys.stdout patched with StringIO to capture print() output.
              this is the CI-safe approach. all Option B tests run in CI.
"""

import os
import pty
import subprocess
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from lssql.cli import main


def _ls_sql_bin():
    """
    resolve ls-sql binary relative to the current Python executable.
    guarantees the correct venv binary is used on all platforms including CI.
    """
    bin_dir = os.path.dirname(sys.executable)
    return os.path.join(bin_dir, "ls-sql")


skip_on_ci = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="subprocess stdout capture unreliable on Linux CI on GitHub",
)


# -- Option A: subprocess --


@skip_on_ci
def test_cli_harvest_dry_run_subprocess(tmp_path):
    """subprocess: harvest without --commit prints dry-run summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout
    assert "no files changed" in result.stdout


@skip_on_ci
def test_cli_harvest_commit_subprocess(tmp_path):
    """subprocess: harvest --commit renames file and prints committed summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "committed" in result.stdout
    assert len(list(tmp_path.glob("photo^^^*"))) == 1


@skip_on_ci
def test_cli_verify_exit_code_zero_subprocess(tmp_path):
    """subprocess: verify exits 0 when all files ok."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
    )

    result = subprocess.run(
        [_ls_sql_bin(), "verify", str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0


@skip_on_ci
def test_cli_verify_exit_code_one_subprocess(tmp_path):
    """subprocess: verify exits 1 when a file has changed."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
    )

    harvested = next(iter(tmp_path.glob("photo^^^*")))
    harvested.write_text("tampered content")

    result = subprocess.run(
        [_ls_sql_bin(), "verify", str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1


@skip_on_ci
def test_cli_no_path_subprocess_without_a_terminal():
    """
    subprocess: a bare command word prints help when stdin is not a terminal.

    Paired with the pty test below. Both bind stdin explicitly rather than
    inheriting pytest's, so neither result depends on how the suite was
    launched: a terminal from a shell, something else under nohup, cron, or an
    editor. An inherited-stdin version of this test passed or failed with the
    launch context rather than with the code.
    """
    with open(os.devnull) as devnull:
        result = subprocess.run(
            [_ls_sql_bin(), "harvest"],
            stdin=devnull,
            capture_output=True,
            check=False,
            text=True,
        )

    assert result.returncode == 0
    assert "ls-sql harvest " in result.stdout


@skip_on_ci
def test_cli_no_path_subprocess_with_a_terminal():
    """subprocess: same answer when stdin really is a terminal."""
    # a real pty, so this is the interactive case and not a simulation of it
    primary, secondary = pty.openpty()
    try:
        result = subprocess.run(
            [_ls_sql_bin(), "harvest"],
            stdin=secondary,
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        os.close(primary)
        os.close(secondary)

    assert result.returncode == 0
    assert "ls-sql harvest " in result.stdout


# -- Option B: main() direct --


def test_cli_harvest_dry_run_main(tmp_path, freeze_date):
    """main(): harvest without --commit prints dry-run summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed" in mock_out.getvalue()


def test_cli_harvest_commit_main(tmp_path, freeze_date):
    """main(): harvest --commit renames file and prints committed summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "committed" in mock_out.getvalue()
    assert len(list(tmp_path.glob("photo^^^*"))) == 1


def test_cli_reset_main(tmp_path, freeze_date):
    """main(): reset restores original filename."""
    (tmp_path / "photo^^^ls:hd=20260503^^^.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "reset", str(tmp_path), "--commit"],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "committed" in mock_out.getvalue()
    assert (tmp_path / "photo.jpg").exists()


def test_cli_verify_ok_main(tmp_path, freeze_date):
    """main(): verify exits 0 when all files ok."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
        pytest.raises(SystemExit),
    ):
        main()

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "verify", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0


def test_cli_verify_changed_main(tmp_path, freeze_date):
    """main(): verify exits 1 when a file has changed."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
        pytest.raises(SystemExit),
    ):
        main()

    harvested = next(iter(tmp_path.glob("photo^^^*")))
    harvested.write_text("tampered content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "verify", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1


def test_cli_no_path_main():
    """main(): a command with options but no path errors and exits 1."""
    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", "--commit"]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# pipe mode tests
# ---------------------------------------------------------------------------


def test_pipe_mode_plain_filename(tmp_path):
    """
    pipe mode: plain filename piped through stdin is printed as full path.
    """
    fake_input = f"{tmp_path}/photo.jpg\n"

    with (
        patch("lssql.cli.stdin_has_content", return_value=True),
        patch("sys.argv", ["ls-sql"]),
        patch("sys.stdin", StringIO(fake_input)),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "photo.jpg" in mock_out.getvalue()


def test_pipe_mode_hatfile_filename(tmp_path):
    """
    pipe mode: hatfile filename (with ^^^) piped through stdin is echoed back.
    """
    filename = "photo^^^ls:hd=20260503^^^.jpg"
    fake_input = f"{tmp_path}/{filename}\n"

    with (
        patch("lssql.cli.stdin_has_content", return_value=True),
        patch("sys.argv", ["ls-sql"]),
        patch("sys.stdin", StringIO(fake_input)),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert filename in mock_out.getvalue()


def test_pipe_mode_skips_hidden_files(tmp_path):
    """
    pipe mode: hidden files (dot-prefixed) are silently skipped.
    """
    fake_input = f"{tmp_path}/.hidden.jpg\n"

    with (
        patch("lssql.cli.stdin_has_content", return_value=True),
        patch("sys.argv", ["ls-sql"]),
        patch("sys.stdin", StringIO(fake_input)),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert ".hidden" not in mock_out.getvalue()


def test_pipe_mode_multiple_lines(tmp_path):
    """
    pipe mode: multiple filenames piped through stdin are all printed.
    """
    fake_input = (
        f"{tmp_path}/alpha.jpg\n" f"{tmp_path}/beta.jpg\n" f"{tmp_path}/gamma.png\n"
    )

    with (
        patch("lssql.cli.stdin_has_content", return_value=True),
        patch("sys.argv", ["ls-sql"]),
        patch("sys.stdin", StringIO(fake_input)),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    out = mock_out.getvalue()
    assert "alpha.jpg" in out
    assert "beta.jpg" in out
    assert "gamma.png" in out


def test_pipe_mode_empty_stdin():
    """
    pipe mode: empty stdin produces no output and exits 0.
    """
    with (
        patch("lssql.cli.stdin_has_content", return_value=True),
        patch("sys.argv", ["ls-sql"]),
        patch("sys.stdin", StringIO("")),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert mock_out.getvalue() == ""


# -- CLI grammar (mdmap house style) --


def test_cli_bare_invocation_prints_banner_main():
    """main(): bare ls-sql on a TTY prints the docstring banner, exits 0."""
    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql"]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    out = mock_out.getvalue()
    assert "ls-sql" in out
    assert "Usage:" in out
    assert "Exit codes:" in out


def test_cli_missing_path_usage_error_main():
    """main(): a command with options but no path prints error + USAGE, exits 1."""
    with (
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch("sys.argv", ["ls-sql", "harvest", "--commit"]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1
    err = mock_err.getvalue()
    assert "ls-sql: a path is required" in err
    assert "Usage: ls-sql list|harvest|set|verify|reset PATH" in err
    # compact USAGE only -- no full argparse help dump
    assert "show this help message" not in err


def test_cli_target_not_found_error_main(tmp_path):
    """main(): a nonexistent path prints ls-sql: error + USAGE, exits 1."""
    missing = tmp_path / "does-not-exist"

    with (
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch("sys.argv", ["ls-sql", "list", str(missing)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1
    err = mock_err.getvalue()
    assert "ls-sql: directory or file not found" in err
    assert "Usage: ls-sql list|harvest|set|verify|reset PATH" in err


def test_cli_unknown_flag_exits_two_main():
    """main(): an unknown flag is an argparse error, exit 2."""
    with (
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch("sys.argv", ["ls-sql", "list", ".", "--nope"]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 2
    assert "unrecognized arguments" in mock_err.getvalue()


def test_cli_unknown_command_exits_two_main():
    """main(): an unknown command word is an argparse error, exit 2."""
    with (
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch("sys.argv", ["ls-sql", "badcmd", "."]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 2
    assert "invalid choice" in mock_err.getvalue()

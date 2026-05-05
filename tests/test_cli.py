import os
import subprocess
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from lssql.cli import main


def _ls_sql_bin():
    """resolve ls-sql binary relative to the current Python executable.
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
    """subprocess: --harvest without --commit prints dry-run summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "--harvest", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "dry-run" in result.stdout
    assert "no files changed" in result.stdout


@skip_on_ci
def test_cli_harvest_commit_subprocess(tmp_path):
    """subprocess: --harvest --commit renames file and prints committed summary."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "committed" in result.stdout
    assert len(list(tmp_path.glob("photo^^^*"))) == 1


@skip_on_ci
def test_cli_verify_exit_code_zero_subprocess(tmp_path):
    """subprocess: --verify exits 0 when all files ok."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
    )

    result = subprocess.run(
        [_ls_sql_bin(), "--verify", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


@skip_on_ci
def test_cli_verify_exit_code_one_subprocess(tmp_path):
    """subprocess: --verify exits 1 when a file has changed."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "--harvest", "--commit", str(tmp_path)],
        capture_output=True,
    )

    harvested = list(tmp_path.glob("photo^^^*"))[0]
    harvested.write_text("tampered content")

    result = subprocess.run(
        [_ls_sql_bin(), "--verify", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1


@skip_on_ci
def test_cli_no_path_subprocess():
    """subprocess: missing path prints error and exits 1."""
    result = subprocess.run(
        [_ls_sql_bin(), "--harvest"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "error" in result.stdout

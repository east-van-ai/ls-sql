# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
CLI --query mode tests for lssql.
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

import os
import subprocess
from io import StringIO
from unittest.mock import patch

import pytest

from lssql.cli import main
from tests.test_cli import _ls_sql_bin, skip_on_ci

# -- Option A: subprocess --


@skip_on_ci
def test_cli_query_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: --query with a directory as arg
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
        [_ls_sql_bin(), "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "/photo^^^" in result.stdout
    filename = os.path.basename(marked)
    assert filename in result.stdout


@skip_on_ci
def test_cli_query_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: --query with a filename as arg
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
        [_ls_sql_bin(), "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(marked)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "/photo^^^" in result.stdout
    filename = os.path.basename(marked)
    assert filename in result.stdout


# -- Option B: main() direct --


def test_cli_query_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """main(): --query with a directory as arg"""
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
        patch(
            "sys.argv",
            ["ls-sql", "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(tmp_path)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "/photo^^^" in mock_out.getvalue()
    filename = os.path.basename(marked)
    assert filename in mock_out.getvalue()


def test_cli_query_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """main(): --query with a filename as arg"""
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
        patch(
            "sys.argv",
            ["ls-sql", "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(marked)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "/photo^^^" in mock_out.getvalue()
    filename = os.path.basename(marked)
    assert filename in mock_out.getvalue()


# -- hidden files --


def test_cli_query_mode_option_b_directory_containing_hidden_files(
    tmp_path, freeze_date
):
    """main(): --query with a directory as arg"""
    (tmp_path / "aaa.jpg").write_text("fake content")
    (tmp_path / "bbb.jpg").write_text("fake content")
    (tmp_path / "ccc.jpg").write_text("fake content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    # Note: the order may not be [aaa, bbb, ccc]
    files = sorted(tmp_path.glob("???^^^*^^^.jpg"))
    assert len(files) == 3

    # aaa^^^ls:hd=20260503~~^^^.jpg
    assert files[0].stem.startswith("aaa")

    # .bbb^^^ls:hd=20260503~~^^^.jpg
    assert files[1].stem.startswith("bbb")
    files[1].rename(files[1].parent / ("." + files[1].stem + files[1].suffix))

    # .ccc^^^ls:hd=20260503~~^^^
    assert files[2].stem.startswith("ccc")
    files[2].rename(files[2].parent / ("." + files[2].stem))

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(tmp_path)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "/aaa^^^" in mock_out.getvalue()
    assert "/.bbb^^^" not in mock_out.getvalue()
    assert "/.ccc^^^" not in mock_out.getvalue()


def test_cli_query_mode_option_b_hidden_filename_with_extension(tmp_path, freeze_date):
    """main(): --query with a hidden filename WITH extension as arg"""
    (tmp_path / "bbb.jpg").write_text("fake content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    marked = next(tmp_path.glob("bbb^^^*^^^.jpg"))
    assert marked is not None

    # .bbb^^^ls:hd=20260503~~^^^.jpg
    assert marked.stem.startswith("bbb")
    marked = marked.rename(marked.parent / ("." + marked.stem + marked.suffix))

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(marked)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "/.bbb^^^" not in mock_out.getvalue()


def test_cli_query_mode_option_b_hidden_filename_without_extension(
    tmp_path, freeze_date
):
    """main(): --query with a hidden filename WITHOUT extension as arg"""
    (tmp_path / "ccc.jpg").write_text("fake content")

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "--harvest", "--commit", str(tmp_path)]),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    marked = next(tmp_path.glob("ccc^^^*^^^.jpg"))
    assert marked is not None

    # .ccc^^^ls:hd=20260503~~^^^
    assert marked.stem.startswith("ccc")
    marked = marked.rename(marked.parent / ("." + marked.stem))
    print(marked)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--query", "SELECT * WHERE ls:hd IS NOT NULL", str(marked)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "/.ccc^^^" not in mock_out.getvalue()

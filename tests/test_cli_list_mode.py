"""
CLI list mode tests for lssql.
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
import subprocess
from io import StringIO
from unittest.mock import patch

from lssql.args import EXIT_OK
from lssql.cli import main
from tests.test_cli import _ls_sql_bin, skip_on_ci

# -- Option A: subprocess --


@skip_on_ci
def test_cli_list_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: --query with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
        text=True,
    )

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "list",
            str(tmp_path),
            "--query",
            "SELECT * WHERE ls:hd IS NOT NULL",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "/photo^^^" in result.stdout
    filename = os.path.basename(marked)
    assert filename in result.stdout


@skip_on_ci
def test_cli_list_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: --query with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
        text=True,
    )

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "list",
            str(marked),
            "--query",
            "SELECT * WHERE ls:hd IS NOT NULL",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "/photo^^^" in result.stdout
    filename = os.path.basename(marked)
    assert filename in result.stdout


# -- Option B: main() direct --


def test_cli_list_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """main(): --query with a directory as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        main()

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "list",
                str(tmp_path),
                "--query",
                "SELECT * WHERE ls:hd IS NOT NULL",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "/photo^^^" in mock_out.getvalue()
    filename = os.path.basename(marked)
    assert filename in mock_out.getvalue()


def test_cli_list_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """main(): --query with a filename as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        main()

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "list",
                str(marked),
                "--query",
                "SELECT * WHERE ls:hd IS NOT NULL",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "/photo^^^" in mock_out.getvalue()
    filename = os.path.basename(marked)
    assert filename in mock_out.getvalue()


# -- hidden files --


def test_cli_list_mode_option_b_directory_containing_hidden_files(
    tmp_path, freeze_date
):
    """main(): --query with a directory as arg"""
    (tmp_path / "aaa.jpg").write_text("fake content")
    (tmp_path / "bbb.jpg").write_text("fake content")
    (tmp_path / "ccc.jpg").write_text("fake content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

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
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "list",
                str(tmp_path),
                "--query",
                "SELECT * WHERE ls:hd IS NOT NULL",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "/aaa^^^" in mock_out.getvalue()
    assert "/.bbb^^^" not in mock_out.getvalue()
    assert "/.ccc^^^" not in mock_out.getvalue()


def test_cli_list_mode_option_b_hidden_filename_with_extension(tmp_path, freeze_date):
    """main(): --query with a hidden filename WITH extension as arg"""
    (tmp_path / "bbb.jpg").write_text("fake content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    marked = next(tmp_path.glob("bbb^^^*^^^.jpg"))
    assert marked is not None

    # .bbb^^^ls:hd=20260503~~^^^.jpg
    assert marked.stem.startswith("bbb")
    marked = marked.rename(marked.parent / ("." + marked.stem + marked.suffix))

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "list",
                str(marked),
                "--query",
                "SELECT * WHERE ls:hd IS NOT NULL",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "/.bbb^^^" not in mock_out.getvalue()


def test_cli_list_mode_option_b_hidden_filename_without_extension(
    tmp_path, freeze_date
):
    """main(): --query with a hidden filename WITHOUT extension as arg"""
    (tmp_path / "ccc.jpg").write_text("fake content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    marked = next(tmp_path.glob("ccc^^^*^^^.jpg"))
    assert marked is not None

    # .ccc^^^ls:hd=20260503~~^^^
    assert marked.stem.startswith("ccc")
    marked = marked.rename(marked.parent / ("." + marked.stem))
    print(marked)

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "list",
                str(marked),
                "--query",
                "SELECT * WHERE ls:hd IS NOT NULL",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "/.ccc^^^" not in mock_out.getvalue()

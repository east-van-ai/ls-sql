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

import subprocess
from io import StringIO
from unittest.mock import patch

from lssql.args import EXIT_OK
from lssql.cli import main
from tests.test_cli import _ls_sql_bin, skip_on_ci

# -- Option A: subprocess --


@skip_on_ci
def test_cli_harvest_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: harvest with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path), "--commit"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


@skip_on_ci
def test_cli_harvest_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: harvest with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "harvest", str(tmp_path / "photo.jpg"), "--commit"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


# -- Option B: main() direct --


def test_cli_harvest_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """
    main(): harvest with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    assert code == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


def test_cli_harvest_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """
    main(): harvest with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            ["ls-sql", "harvest", str(tmp_path / "photo.jpg"), "--commit"],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


# -- hidden files --


def test_cli_harvest_mode_option_b_directory_containing_hidden_files(
    tmp_path, freeze_date
):
    """
    main(): harvest mode correctly processes filenames starting with a period (hidden files).
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    (tmp_path / ".hidden-image.jpg").write_text("fake hidden image content")
    (tmp_path / ".hidden-file").write_text("fake content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert not (tmp_path / "photo.jpg").exists()  # renamed by harvester
    assert (tmp_path / ".hidden-image.jpg").exists()
    assert (tmp_path / ".hidden-file").exists()
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None


def test_cli_harvest_mode_option_b_hidden_filename(tmp_path, freeze_date):
    """
    main(): harvest mode correctly processes a filename starting with a period (hidden file)
    """
    (tmp_path / ".photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "harvest", str(tmp_path / ".photo.jpg"), "--commit"],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert (tmp_path / ".photo.jpg").exists()


# -- issue #28: malformed stems are never rewritten --


def test_cli_harvest_mode_option_b_malformed_stem_is_skipped(tmp_path, freeze_date):
    """
    main(): harvest skips a stem whose caret run is not a multiple of three.

    regression for malformed stems parse issue. the seven-caret name used to harvest
    successfully and emit a four-caret one, manufacturing the shape that
    let set destroy the comment text.
    """
    seven = "0001-01234^^^^^^^it-is-blue.jpg"
    four = "0001-01234^^^^it-is-blue.jpg"
    (tmp_path / seven).write_text("fake image content")
    (tmp_path / four).write_text("other fake content")

    mock_out = StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "0 file(s) committed, 2 skipped" in mock_out.getvalue()
    assert (tmp_path / seven).exists()
    assert (tmp_path / four).exists()


def test_cli_harvest_mode_option_b_empty_tag_section_still_harvests(
    tmp_path, freeze_date
):
    """
    main(): a six-caret stem is well-formed and still harvests.

    guards the rule against overreach.
    """
    (tmp_path / "0001-01234^^^^^^it-is-blue.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path), "--commit"]),
    ):
        code = main()

    assert code == EXIT_OK
    marked = next(tmp_path.glob("0001-01234^^^ls:*^^^it-is-blue.jpg"))
    assert marked is not None

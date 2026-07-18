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
              sys.stdin.isatty must be patched to True -- pytest's capturing
              makes isatty() return False, which triggers piped mode in cli.py.
              sys.stdout patched with StringIO to capture print() output.
              this is the CI-safe approach. all Option B tests run in CI.
"""

import subprocess
from io import StringIO
from pathlib import Path
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


# -- hidden files --


def test_cli_set_mode_option_b_directory_containing_hidden_files(tmp_path, freeze_date):
    """main(): --set with a directory as arg"""
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
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green;red" in mock_out.getvalue()


def test_cli_set_mode_option_b_hidden_filename_with_extension(tmp_path, freeze_date):
    """main(): --set with a hidden filename WITH extension as arg"""
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
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
                str(marked),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_hidden_filename_without_extension(tmp_path, freeze_date):
    """main(): --set with a hidden filename WITHOUT extension as arg"""
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
            [
                "ls-sql",
                "--set",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
                str(marked),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()


# -- helpers --


def _harvest_file(tmp_path, filename, content="fake content", freeze=None):
    """
    harvest-commit a single file and return the resulting Path.
    freeze is the freeze_date fixture passed in from the test.
    """
    (tmp_path / filename).write_text(content)

    argv = ["ls-sql", "--harvest", "--commit", str(tmp_path)]
    ctx = [
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", argv),
    ]
    with ctx[0], ctx[1], ctx[2], pytest.raises(SystemExit):
        main()

    # return the renamed file (only one jpg in tmp_path)
    stem = filename.rsplit(".", 1)[0]
    ext = filename.rsplit(".", 1)[1]
    matches = list(tmp_path.glob(f"{stem}^^^*.{ext}"))
    assert matches, f"harvest produced no file matching {stem}^^^*.{ext}"
    return matches[0]


def _extract_fh(harvested_path: Path) -> str:
    """
    pull the ls:fh value out of the harvested filename.
    filename format: stem^^^tag=val^tag=val^^^.ext
    """
    name = harvested_path.stem  # everything before the last dot
    parts = name.split("^^^")
    for part in parts:
        for segment in part.split("^"):
            if segment.startswith("ls:fh="):
                return segment[len("ls:fh=") :]
    raise ValueError(f"ls:fh not found in: {harvested_path.name}")


# -- --fh options --


def test_set_fh_dry_run_matches_file(tmp_path, freeze_date):
    """
    main(): --fh dry-run matches file by hash prefix and prints dry-run.
    """
    harvested = _harvest_file(tmp_path, "photo.jpg", freeze=freeze_date)
    fh = _extract_fh(harvested)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            ["ls-sql", "--set", "ud:tag=hello", "--fh", fh[:8], str(tmp_path)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    out = mock_out.getvalue()
    assert exc.value.code == 0
    assert "dry-run" in out
    assert "no files changed" in out


def test_set_fh_commit_renames_file(tmp_path, freeze_date):
    """
    main(): --fh --commit applies tag to the matched file.
    """
    harvested = _harvest_file(tmp_path, "photo.jpg", freeze=freeze_date)
    fh = _extract_fh(harvested)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "ud:greeting=hello",
                "--fh",
                fh[:8],
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "committed" in mock_out.getvalue()
    tagged = list(tmp_path.glob("photo^^^*ud:greeting=hello*"))
    assert tagged, "expected a file with ud:greeting=hello in its name"


def test_set_fh_no_match_exits_one(tmp_path, freeze_date):
    """
    main(): --fh with a hash that matches nothing exits 1 with error.
    """
    _harvest_file(tmp_path, "photo.jpg", freeze=freeze_date)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch(
            "sys.argv",
            ["ls-sql", "--set", "ud:greeting=hello", "--fh", "00000000", str(tmp_path)],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1
    assert "no files matched --fh hashes" in mock_err.getvalue()


def test_set_fh_prefix_matches_correct_file(tmp_path, freeze_date):
    """
    main(): --fh prefix selects only the matching file, not others.
    """
    h1 = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    _harvest_file(tmp_path, "beta.jpg", content="content-beta", freeze=freeze_date)

    fh_alpha = _extract_fh(h1)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "--set",
                "ud:label=alpha-only",
                "--fh",
                fh_alpha[:8],
                "--commit",
                str(tmp_path),
            ],
        ),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 0
    assert "1 file(s) committed" in mock_out.getvalue()
    # beta untouched
    beta_tagged = list(tmp_path.glob("beta^^^*ud:label=alpha-only*"))
    assert not beta_tagged, "beta should not have been tagged"

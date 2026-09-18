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
from pathlib import Path
from unittest.mock import patch

from lssql.args import EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK
from lssql.cli import main
from tests.test_cli import _ls_sql_bin, skip_on_ci

# -- Option A: subprocess --


@skip_on_ci
def test_cli_set_mode_option_a_directory_as_arg(tmp_path):
    """
    subprocess: set with a directory as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    assert (tmp_path / "photo.jpg").exists()

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=green;blue",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in result.stdout
    assert "my-custom-tag:colour=blue;green" in str(marked)


@skip_on_ci
def test_cli_set_mode_option_a_filename_as_arg(tmp_path):
    """
    subprocess: set with a filename as arg
    """
    (tmp_path / "photo.jpg").write_text("fake image content")
    assert (tmp_path / "photo.jpg").exists()

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path / "photo.jpg"),
            "--tags",
            "my-custom-tag:colour=green;blue",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK

    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in result.stdout
    assert "my-custom-tag:colour=blue;green" in str(marked)


@skip_on_ci
def test_cli_set_mode_option_a_no_set_arg(tmp_path):
    """subprocess: --tags given with no value is an argparse error"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [_ls_sql_bin(), "set", str(tmp_path), "--tags", "--commit"],
        capture_output=True,
        check=False,
    )

    assert result.returncode == EXIT_ARGPARSE


@skip_on_ci
def test_cli_set_mode_option_a_implicit_dry_run(tmp_path):
    """subprocess: implicit dry-run"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=blue;green",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "dry-run" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_explicit_dry_run(tmp_path):
    """subprocess: explicit dry-run"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=blue;green",
            "--dry-run",  # explicit dry-run
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "dry-run" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_overwrite_operation(tmp_path):
    """subprocess: set with = overwrite operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=red",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=green;blue",  # = overwrite operation
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "my-custom-tag:colour=blue;green" in result.stdout  # alphabetical order
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_append_operation(tmp_path):
    """subprocess: set with += append"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=red;green",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour+=red;blue;blue;green",  # += append operation
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "my-custom-tag:colour=blue;green;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_remove_operation(tmp_path):
    """subprocess: set with -= remove operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=red;green;blue",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour-=green",  # -= remove operation
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "my-custom-tag:colour=blue;red" in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


@skip_on_ci
def test_cli_set_mode_option_a_delete_operation(tmp_path):
    """subprocess: set with == delete operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour=green;blue",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    result = subprocess.run(
        [
            _ls_sql_bin(),
            "set",
            str(tmp_path),
            "--tags",
            "my-custom-tag:colour==",
            "--commit",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == EXIT_OK
    assert "dry-run" not in result.stdout
    assert "1 file(s) committed, 0 skipped" in result.stdout


# -- Option B: main() direct --


def test_cli_set_mode_option_b_directory_as_arg(tmp_path, freeze_date):
    """main(): set with a directory as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour=green;blue",
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in str(marked)


def test_cli_set_mode_option_b_filename_as_arg(tmp_path, freeze_date):
    """main(): set with a filename as arg"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path / "photo.jpg"),
                "--tags",
                "my-custom-tag:colour=green;blue",
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    marked = next(tmp_path.glob("photo^^^*^^^.jpg"))
    assert marked is not None

    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in str(marked)


def test_cli_set_mode_option_b_no_tags_arg(tmp_path, freeze_date):
    """main(): set without --tags errors and exits 1."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", ["ls-sql", "set", str(tmp_path)]),
    ):
        code = main()

    assert code == EXIT_ERROR


def test_cli_set_mode_option_b_implicit_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour=green;blue",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed -- pass --commit to execute" in mock_out.getvalue()


def test_cli_set_mode_option_b_explicit_dry_run(tmp_path, freeze_date):
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour=green;blue",
                "--dry-run",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed -- pass --commit to execute" in mock_out.getvalue()


def test_cli_set_mode_option_b_overwrite(tmp_path, freeze_date):
    """subprocess: set with = overwrite operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour=green;blue",  # = overwrite operation
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "dry-run" not in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_append(tmp_path, freeze_date):
    """subprocess: set with += append operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path / "photo.jpg"),
                "--tags",
                "my-custom-tag:colour=blue",
                "--commit",
            ],
        ),
    ):
        main()

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour+=red;blue;blue;green",  # += append operation
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "my-custom-tag:colour=blue;green;red" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_remove(tmp_path, freeze_date):
    """subprocess: set with -= remove operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path / "photo.jpg"),
                "--tags",
                "my-custom-tag:colour=blue;green;red",
                "--commit",
            ],
        ),
    ):
        main()

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour-=green",  # -= remove operation
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "my-custom-tag:colour=blue;red" in mock_out.getvalue()
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_delete(tmp_path, freeze_date):
    """subprocess: set with == delete operation"""
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path / "photo.jpg"),
                "--tags",
                "my-custom-tag:colour=blue;green;red",
                "--commit",
            ],
        ),
    ):
        main()

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour==",  # == delete operation
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()


# -- hidden files --


def test_cli_set_mode_option_b_directory_containing_hidden_files(tmp_path, freeze_date):
    """main(): set with a directory as arg"""
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
                "set",
                str(tmp_path),
                "--tags",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "1 file(s) committed, 0 skipped" in mock_out.getvalue()
    assert "my-custom-tag:colour=blue;green;red" in mock_out.getvalue()


def test_cli_set_mode_option_b_hidden_filename_with_extension(tmp_path, freeze_date):
    """main(): set with a hidden filename WITH extension as arg"""
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
                "set",
                str(marked),
                "--tags",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()


def test_cli_set_mode_option_b_hidden_filename_without_extension(tmp_path, freeze_date):
    """main(): set with a hidden filename WITHOUT extension as arg"""
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
                "set",
                str(marked),
                "--tags",
                "my-custom-tag:colour=red;blue;green",
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "0 file(s) committed, 0 skipped" in mock_out.getvalue()


# -- helpers --


def _harvest_file(tmp_path, filename, content="fake content", freeze=None):
    """
    harvest-commit a single file and return the resulting Path.
    freeze is the freeze_date fixture passed in from the test.
    """
    (tmp_path / filename).write_text(content)

    argv = ["ls-sql", "harvest", str(tmp_path), "--commit"]
    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.argv", argv),
    ):
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
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "ud:tag=hello",
                "--fh",
                fh[:8],
            ],
        ),
    ):
        code = main()

    out = mock_out.getvalue()
    assert code == EXIT_OK
    assert "dry-run" in out
    assert "no files changed" in out


def test_set_fh_commit_renames_file(tmp_path, freeze_date):
    """
    main(): --fh --commit applies tag to the matched file.
    """
    harvested = _harvest_file(tmp_path, "photo.jpg", freeze=freeze_date)
    fh = _extract_fh(harvested)

    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "ud:greeting=hello",
                "--fh",
                fh[:8],
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "committed" in mock_out.getvalue()
    tagged = list(tmp_path.glob("photo^^^*ud:greeting=hello*"))
    assert tagged, "expected a file with ud:greeting=hello in its name"


def test_set_fh_no_match_exits_one(tmp_path, freeze_date):
    """
    main(): --fh with a hash that matches nothing exits 1 with error.
    """
    _harvest_file(tmp_path, "photo.jpg", freeze=freeze_date)

    with (
        patch("sys.stdout", new_callable=StringIO),
        patch("sys.stderr", new_callable=StringIO) as mock_err,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "ud:greeting=hello",
                "--fh",
                "00000000",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_ERROR
    assert "no file matched --fh: 00000000" in mock_err.getvalue()


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
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch(
            "sys.argv",
            [
                "ls-sql",
                "set",
                str(tmp_path),
                "--tags",
                "ud:label=alpha-only",
                "--fh",
                fh_alpha[:8],
                "--commit",
            ],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "1 file(s) committed" in mock_out.getvalue()
    # beta untouched
    beta_tagged = list(tmp_path.glob("beta^^^*ud:label=alpha-only*"))
    assert not beta_tagged, "beta should not have been tagged"


# -- --fh prefixes stand on their own --


def _set_by_fh(tmp_path, fh_arg, extra=()):
    """
    run set --fh against tmp_path, and return (exit code, stdout, stderr).
    """
    argv = [
        "ls-sql",
        "set",
        str(tmp_path),
        "--tags",
        "ud:x=1",
        "--fh",
        fh_arg,
        *extra,
    ]
    mock_out, mock_err = StringIO(), StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch("sys.stderr", new=mock_err),
        patch("sys.argv", argv),
    ):
        code = main()
    return code, mock_out.getvalue(), mock_err.getvalue()


def test_set_fh_mixed_length_prefixes_match_every_file(tmp_path, freeze_date):
    """
    main(): --fh prefixes of different lengths each match on their own length.

    regression. The old predicate sliced every stored hash to the length of one
    arbitrary member of a set, then compared for equality, so any prefix of a
    different length was silently dead and the run still exited 0.
    """
    a = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    b = _harvest_file(tmp_path, "beta.jpg", content="content-beta", freeze=freeze_date)

    short, full = _extract_fh(a)[:4], _extract_fh(b)

    code, out, _ = _set_by_fh(tmp_path, f"{short},{full}")

    assert code == EXIT_OK
    assert "2 file(s) dry-run" in out


def test_set_fh_unmatched_prefix_stops_the_whole_run(tmp_path, freeze_date):
    """
    main(): one prefix matching nothing refuses the batch, matches included.
    """
    a = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    good = _extract_fh(a)[:8]

    code, out, err = _set_by_fh(tmp_path, f"{good},00000000", extra=("--commit",))

    assert code == EXIT_ERROR
    assert "no file matched --fh: 00000000" in err
    assert "committed" not in out
    assert list(tmp_path.glob("alpha^^^*")) == [a], "the matched file must be untouched"


def test_set_fh_missing_prefixes_are_all_named(tmp_path, freeze_date):
    """
    main(): the error names every prefix that found nothing, in typed order.
    """
    _harvest_file(tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date)

    code, _, err = _set_by_fh(tmp_path, "ffffffff,00000000")

    assert code == EXIT_ERROR
    assert "no file matched --fh: ffffffff, 00000000" in err


def test_set_fh_trailing_comma_is_not_a_wildcard(tmp_path, freeze_date):
    """
    main(): an empty prefix is dropped, not treated as matching every row.

    "".startswith() is true for every hash, so a surviving empty prefix would
    silently widen the selection to the whole directory.
    """
    a = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    _harvest_file(tmp_path, "beta.jpg", content="content-beta", freeze=freeze_date)

    code, out, _ = _set_by_fh(tmp_path, f"{_extract_fh(a)[:8]},")

    assert code == EXIT_OK
    assert "1 file(s) dry-run" in out


def test_set_fh_only_separators_is_an_error(tmp_path, freeze_date):
    """
    main(): --fh with nothing usable in it is an error, not a match-all.
    """
    _harvest_file(tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date)

    code, _, err = _set_by_fh(tmp_path, ",")

    assert code == EXIT_ERROR
    assert "--fh needs at least one hash prefix" in err


def test_set_empty_fh_commit_is_an_error(tmp_path, freeze_date):
    """
    main(): an empty --fh is refused, and no file is renamed.

    regression. An empty --fh read the same as an absent one, so the run fell
    through to the path and committed every file under it. An unset shell
    variable in --fh "$HASH" is the natural way to hit it.
    """
    a = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    b = _harvest_file(tmp_path, "beta.jpg", content="content-beta", freeze=freeze_date)

    code, out, err = _set_by_fh(tmp_path, "", extra=("--commit",))

    assert code == EXIT_ERROR
    assert "--fh needs at least one hash prefix" in err
    assert out == ""
    assert sorted(tmp_path.iterdir()) == sorted([a, b]), "no file may be renamed"


def test_set_empty_fh_dry_run_is_an_error(tmp_path, freeze_date):
    """
    main(): an empty --fh is refused before a dry run previews anything.
    """
    _harvest_file(tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date)

    code, out, err = _set_by_fh(tmp_path, "")

    assert code == EXIT_ERROR
    assert "--fh needs at least one hash prefix" in err
    assert out == ""


def test_set_fh_duplicate_prefixes_match_once(tmp_path, freeze_date):
    """
    main(): the same prefix twice selects its file once, and is not an error.
    """
    a = _harvest_file(
        tmp_path, "alpha.jpg", content="content-alpha", freeze=freeze_date
    )
    prefix = _extract_fh(a)[:8]

    code, out, _ = _set_by_fh(tmp_path, f"{prefix},{prefix}")

    assert code == EXIT_OK
    assert "1 file(s) dry-run" in out


# -- malformed stems are never rewritten --


def test_cli_set_mode_option_b_malformed_stem_is_not_rewritten(tmp_path, freeze_date):
    """
    main(): set leaves a stem with a stray caret run alone.

    regression for malformed stems parse issue. a four-caret run put '^it-is-blue' in the tag
    slot, is_already_harvested() read that as real tags, and set overwrote the
    section -- destroying 'it-is-blue' with no way to recover it from the
    filename.
    """
    name = "0001-01234^^^^it-is-blue.jpg"
    (tmp_path / name).write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            ["ls-sql", "set", str(tmp_path), "--tags", "ud:colour=blue", "--commit"],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "0 file(s) committed, 1 skipped" in mock_out.getvalue()
    assert (tmp_path / name).exists(), "the malformed file must be untouched"
    assert "it-is-blue" in (tmp_path / name).name


def test_cli_set_mode_option_b_empty_tag_section_still_works(tmp_path, freeze_date):
    """
    main(): a six-caret stem is well-formed and still accepts a tag.

    guards the rule against overreach -- 'original^^^^^^comment' is a
    harvested file with an empty tag section, not a malformed name.
    """
    (tmp_path / "0001-01234^^^^^^it-is-blue.jpg").write_text("fake image content")

    mock_out = StringIO()
    with (
        patch("sys.stdout", new=mock_out),
        patch(
            "sys.argv",
            ["ls-sql", "set", str(tmp_path), "--tags", "ud:colour=blue", "--commit"],
        ),
    ):
        code = main()

    assert code == EXIT_OK
    assert "1 file(s) committed" in mock_out.getvalue()
    tagged = next(tmp_path.glob("0001-01234^^^*ud:colour=blue*^^^it-is-blue.jpg"))
    assert tagged is not None

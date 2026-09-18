"""
tests pinning the shared rename-preview format.

harvest, set, and reset print the same shape, and until this file
existed nothing asserted it. Every other CLI test checks substrings like
"dry-run" in the output, which cannot see indentation, so the three modes had
drifted into two different status-column widths without anything noticing.

These tests assert exact line prefixes on purpose. If the format is changed
deliberately, they are meant to fail and be updated.

Option B throughout: main() called directly with mocked sys.argv.
"""

from io import StringIO
from unittest.mock import patch

from lssql.cli import main
from lssql.shared import STATUS_WIDTH


def _run(argv):
    """call main() with argv and return captured stdout."""
    with (
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql"] + argv),
    ):
        main()
    return mock_out.getvalue()


def _prefix(word):
    """the expected leading text of a preview line for a given status word."""
    return f"  {word:>{STATUS_WIDTH}} : "


# -- the status column is the same width in every mode --


def test_harvest_preview_uses_the_shared_column(tmp_path, freeze_date):
    """harvest: status and arrow lines share the STATUS_WIDTH column."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    out = _run(["harvest", str(tmp_path)])
    lines = out.splitlines()

    assert lines[0].startswith(_prefix("dry-run"))
    assert lines[1].startswith(_prefix("->"))


def test_set_preview_uses_the_shared_column(tmp_path, freeze_date):
    """set: status and arrow lines share the STATUS_WIDTH column."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    out = _run(["set", str(tmp_path), "--tags", "ud:tag=x"])
    lines = out.splitlines()

    assert lines[0].startswith(_prefix("dry-run"))
    assert lines[1].startswith(_prefix("->"))


def test_remove_preview_uses_the_shared_column(tmp_path, freeze_date):
    """reset: status and arrow lines share the STATUS_WIDTH column."""
    (tmp_path / "photo^^^ls:hd=20260503^^^.jpg").write_text("fake image content")

    out = _run(["reset", str(tmp_path)])
    lines = out.splitlines()

    assert lines[0].startswith(_prefix("dry-run"))
    assert lines[1].startswith(_prefix("->"))


def test_every_mode_aligns_on_the_same_column(tmp_path, freeze_date):
    """
    the three rename modes agree on where the ` : ` column sits.

    This is the regression the shared printer exists for: reset used
    to pad to 8 because "restored" is eight characters, while harvest and set
    padded to 7, so the same status word printed at two different indents.
    """
    harvest_dir = tmp_path / "h"
    set_dir = tmp_path / "s"
    remove_dir = tmp_path / "r"
    for d in (harvest_dir, set_dir, remove_dir):
        d.mkdir()
    (harvest_dir / "photo.jpg").write_text("fake image content")
    (set_dir / "photo.jpg").write_text("fake image content")
    (remove_dir / "photo^^^ls:hd=20260503^^^.jpg").write_text("fake image content")

    outs = [
        _run(["harvest", str(harvest_dir)]),
        _run(["set", str(set_dir), "--tags", "ud:tag=x"]),
        _run(["reset", str(remove_dir)]),
    ]

    columns = {out.splitlines()[0].index(" : ") for out in outs}
    assert len(columns) == 1, f"modes disagree on the status column: {columns}"


def test_restored_fits_the_column_without_overflowing(tmp_path, freeze_date):
    """
    "restored" is the longest status word and must not push the column right.

    A width of 7 would still print the whole word, just misaligned against the
    arrow line, which is exactly the bug this pins.
    """
    (tmp_path / "photo^^^ls:hd=20260503^^^.jpg").write_text("fake image content")

    out = _run(["reset", str(tmp_path), "--commit"])
    lines = out.splitlines()

    assert lines[0].startswith(_prefix("restored"))
    assert lines[0].index(" : ") == lines[1].index(" : ")


# -- skipped lines and the summary tail --


def test_skipped_line_needs_verbose(tmp_path, freeze_date):
    """skipped files print only under --verbose, with the reason in parens."""
    (tmp_path / "note.txt").write_text("not a harvestable extension")

    quiet = _run(["harvest", str(tmp_path)])
    loud = _run(["harvest", str(tmp_path), "--verbose"])

    assert "note.txt" not in quiet
    assert loud.startswith(_prefix("skipped"))
    assert "note.txt  (" in loud


def test_summary_tail_and_dry_run_hint(tmp_path, freeze_date):
    """the tail counts actioned and skipped, and the hint appears without --commit."""
    (tmp_path / "photo.jpg").write_text("fake image content")
    (tmp_path / "note.txt").write_text("skipped by extension")

    out = _run(["harvest", str(tmp_path)])

    assert "\n1 file(s) dry-run, 1 skipped\n" in out
    assert out.endswith("  (no files changed -- pass --commit to execute)\n")


def test_commit_tail_drops_the_hint(tmp_path, freeze_date):
    """with --commit the tail says committed and the dry-run hint is gone."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    out = _run(["harvest", str(tmp_path), "--commit"])

    assert "\n1 file(s) committed, 0 skipped\n" in out
    assert "no files changed" not in out


# -- the directory prefix --


def test_directory_prefix_appears_only_under_recursive(tmp_path, freeze_date):
    """-R prefixes each file with its directory; without it, bare filenames."""
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "photo.jpg").write_text("fake image content")

    recursive = _run(["harvest", str(tmp_path), "-R"])
    flat = _run(["harvest", str(tmp_path)])

    assert f"{nested}/photo.jpg" in recursive
    assert "photo.jpg" not in flat


def test_fh_preview_shows_the_directory_prefix(tmp_path, freeze_date):
    """
    set --fh -R prefixes matches with their directory, same as plain set.

    The --fh branch used to print bare filenames, so two files sharing a
    basename in different directories were indistinguishable in the preview.
    """
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "photo.jpg").write_text("fake image content")

    _run(["harvest", str(tmp_path), "--commit", "-R"])
    harvested = next(iter(nested.glob("photo^^^*.jpg")))
    fh = harvested.name.split("ls:fh=")[1].split("^")[0]

    out = _run(["set", str(tmp_path), "--tags", "ud:tag=y", "--fh", fh, "-R"])

    assert f"{nested}/{harvested.name}" in out

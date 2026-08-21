"""
tests for cli.stdin_has_content() and the piped-mode gate it drives.

"piped" is a file type, not the absence of a terminal. isatty() cannot tell
a pipe from /dev/null, and /dev/null is what cron, systemd, nohup, and CI
runners hand a process. These tests pin that distinction against real file
descriptors rather than mocks, since the whole point is what fstat() reports.

The last test is the regression: an unattended harvest must harvest, not
fall through to passthrough and silently do nothing.
"""

import os
from io import StringIO
from unittest.mock import patch

from lssql.args import EXIT_OK
from lssql.cli import main, stdin_has_content

# -- content: pipes, redirects, sockets --


def test_stdin_has_content_true_for_pipe():
    """a real FIFO counts as piped input."""
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(read_fd, "r") as reader, patch("sys.stdin", reader):
            assert stdin_has_content() is True
    finally:
        os.close(write_fd)


def test_stdin_has_content_true_for_redirected_file(tmp_path):
    """`ls-sql < paths.txt` counts as piped input."""
    source = tmp_path / "paths.txt"
    source.write_text("photo.jpg\n")

    with open(source) as handle, patch("sys.stdin", handle):
        assert stdin_has_content() is True


# -- not content: terminals, /dev/null, no descriptor --


def test_stdin_has_content_false_for_devnull():
    """
    /dev/null is not content. This is the cron and systemd case.

    A character device, exactly like a terminal, which is why isatty() alone
    cannot separate the two.
    """
    with open(os.devnull) as handle, patch("sys.stdin", handle):
        assert stdin_has_content() is False


def test_stdin_has_content_false_for_terminal():
    """a terminal is never piped content, and short-circuits before fstat."""

    class FakeTTY:
        def isatty(self):
            return True

    with patch("sys.stdin", FakeTTY()):
        assert stdin_has_content() is False


def test_stdin_has_content_false_when_stdin_is_none():
    """a closed stdin (sys.stdin is None) is not content."""
    with patch("sys.stdin", None):
        assert stdin_has_content() is False


def test_stdin_has_content_false_without_a_real_descriptor():
    """
    a StringIO has no fileno(), so it is not content.

    This is also what pytest's capturing hands the suite, which is why Option B
    tests no longer need to patch isatty to keep piped mode switched off.
    """
    with patch("sys.stdin", StringIO("photo.jpg\n")):
        assert stdin_has_content() is False


def test_stdin_has_content_false_under_pytest_capture():
    """the suite's own stdin does not read as piped input."""
    assert stdin_has_content() is False


# -- the regression --


def test_unattended_harvest_is_not_treated_as_piped(tmp_path, freeze_date):
    """
    harvest with stdin on /dev/null harvests instead of silently passing through.

    The cron case. Before the file-type test, this printed nothing, renamed
    nothing, and exited 0.
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    with (
        open(os.devnull) as devnull,
        patch("sys.stdin", devnull),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql", "harvest", str(tmp_path)]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "dry-run" in mock_out.getvalue()
    assert "no files changed" in mock_out.getvalue()


def test_unattended_bare_invocation_prints_the_banner(tmp_path):
    """
    bare ls-sql with stdin on /dev/null prints the banner instead of nothing.

    Both before and after the fix this exits 0, but the output differs: the
    old passthrough read zero lines from /dev/null and printed nothing at all.
    """
    with (
        open(os.devnull) as devnull,
        patch("sys.stdin", devnull),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql"]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "ls-sql" in mock_out.getvalue()


def test_piped_paths_still_pass_through(tmp_path):
    """a real pipe still reaches passthrough mode and echoes parsed paths."""
    read_fd, write_fd = os.pipe()
    with os.fdopen(write_fd, "w") as writer:
        writer.write(f"{tmp_path}/photo.jpg\n")

    with (
        os.fdopen(read_fd, "r") as reader,
        patch("sys.stdin", reader),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql"]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "photo.jpg" in mock_out.getvalue()


def test_redirected_file_still_passes_through(tmp_path):
    """a redirected file still reaches passthrough mode."""
    source = tmp_path / "paths.txt"
    source.write_text(f"{tmp_path}/photo.jpg\n")

    with (
        open(source) as handle,
        patch("sys.stdin", handle),
        patch("sys.stdout", new_callable=StringIO) as mock_out,
        patch("sys.argv", ["ls-sql"]),
    ):
        code = main()

    assert code == EXIT_OK
    assert "photo.jpg" in mock_out.getvalue()

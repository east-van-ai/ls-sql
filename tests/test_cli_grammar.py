# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
tests pinning the command-word grammar itself.

ls-sql takes a command word in sys.argv[1] and a path in sys.argv[2]. Both
positions are checked against sys.argv directly rather than left to argparse,
because since Python 3.12 argparse back-fills a trailing optional positional
from a token appearing after any number of flags. Without these tests the
accepted grammar could drift away from the documented one and nothing would
notice: the wrong command line still parses, it just means something else.

See DESIGN.md, "CLI grammar" and "Positions are decided, not inferred".

Option B throughout: main() called directly with mocked sys.argv.
"""

from io import StringIO
from unittest.mock import patch

import pytest

from lssql.cli import main


def _run(argv, stdin_is_tty=False):
    """call main() with argv; return (exit_code, stdout, stderr)."""

    class FakeTTY:
        def isatty(self):
            return stdin_is_tty

        def __iter__(self):
            return iter(())

    with (
        patch("sys.stdout", new_callable=StringIO) as out,
        patch("sys.stderr", new_callable=StringIO) as err,
        patch("sys.stdin", FakeTTY()),
        patch("sys.argv", ["ls-sql"] + argv),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    return exc.value.code, out.getvalue(), err.getvalue()


# -- the command word owns sys.argv[1] --


def test_command_must_come_first(tmp_path):
    """a flag before the command word is a usage error, not a reordering."""
    code, _, err = _run(["--commit", "harvest", str(tmp_path)])

    assert code == 1
    assert "the command must come right after 'ls-sql'" in err
    assert "'--commit' first" in err


def test_unknown_command_is_an_argparse_error(tmp_path):
    """an unrecognised command word exits 2, argparse's own error."""
    code, _, err = _run(["badcmd", str(tmp_path)])

    assert code == 2
    assert "invalid choice" in err


def test_no_command_word_at_all(tmp_path):
    """`ls-sql .` is a usage error: there is no default command."""
    code, _, err = _run([str(tmp_path)])

    assert code == 2
    assert "invalid choice" in err


# -- the path owns sys.argv[2] --


def test_path_is_not_back_filled_from_later_tokens(tmp_path):
    """
    a path after a flag does not count, even though argparse would accept it.

    This is the drift guard. argparse parses `harvest --commit PATH` happily
    with path set; the documented grammar puts the path immediately after the
    command, so the slot is decided on sys.argv[2] alone.
    """
    code, _, err = _run(["harvest", "--commit", str(tmp_path)])

    assert code == 1
    assert "a path is required right after the command" in err


def test_path_right_after_the_command_is_accepted(tmp_path):
    """the documented order works."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    code, out, _ = _run(["harvest", str(tmp_path), "--commit"])

    assert code == 0
    assert "committed" in out


def test_missing_path_is_an_ls_sql_error(tmp_path):
    """
    a command with options but no path errors, exit 1, with compact USAGE.

    Bare `ls-sql harvest` is a help request; this is the case where the user
    asked for something specific and left the path out.
    """
    code, _, err = _run(["harvest", "--commit"])

    assert code == 1
    assert "a path is required right after the command" in err
    assert "Usage: ls-sql list|harvest|set|verify|reset PATH" in err
    # compact USAGE only -- never the full argparse help dump
    assert "show this help message" not in err


def test_bare_command_is_a_help_request():
    """
    a command word and nothing else prints that command's help.

    Bare means literally bare. Once any other argument is present the user
    asked for something specific, and help text would hide the mistake.
    """
    code, out, _ = _run(["harvest"], stdin_is_tty=True)

    assert code == 0
    assert "ls-sql harvest" in out


def test_bare_command_help_does_not_depend_on_stdin():
    """
    the same answer whether or not stdin is a terminal.

    Help used to be gated on isatty(), which made the result depend on how
    ls-sql was launched rather than on what was typed. A suite run under nohup
    or from an editor got a different exit code than the same command in a
    shell.
    """
    on_tty = _run(["harvest"], stdin_is_tty=True)
    off_tty = _run(["harvest"], stdin_is_tty=False)

    assert on_tty == off_tty


# -- options are scoped to their command --


def test_commit_is_rejected_for_list(tmp_path):
    """list never renames, so --commit is an error rather than ignored."""
    code, _, err = _run(["list", str(tmp_path), "--commit"])

    assert code == 1
    assert "--commit is not an option of 'list'" in err


def test_query_is_rejected_for_harvest(tmp_path):
    """--query belongs to list."""
    code, _, err = _run(["harvest", str(tmp_path), "--query", "SELECT * WHERE a='b'"])

    assert code == 1
    assert "--query is not an option of 'harvest'" in err


def test_ext_is_rejected_for_set(tmp_path):
    """--ext belongs to harvest; set selects by path or hash."""
    code, _, err = _run(["set", str(tmp_path), "--tags", "ud:a=1", "--ext", "jpg"])

    assert code == 1
    assert "--ext is not an option of 'set'" in err


def test_fh_is_rejected_for_verify(tmp_path):
    """--fh belongs to set."""
    code, _, err = _run(["verify", str(tmp_path), "--fh", "abc123"])

    assert code == 1
    assert "--fh is not an option of 'verify'" in err


def test_set_requires_tags(tmp_path):
    """set without --tags has nothing to write."""
    code, _, err = _run(["set", str(tmp_path)])

    assert code == 1
    assert "set requires --tags" in err


def test_shared_options_are_accepted_everywhere(tmp_path):
    """-R and --verbose belong to every command."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    for argv in (
        ["list", str(tmp_path), "-R"],
        ["harvest", str(tmp_path), "-R", "--verbose"],
        ["verify", str(tmp_path), "-R", "--verbose"],
        ["reset", str(tmp_path), "-R", "--verbose"],
    ):
        code, _, err = _run(argv)
        assert code == 0, f"{argv} failed: {err}"


# -- paths that do not exist --


def test_missing_directory_is_an_ls_sql_error(tmp_path):
    """a path that is neither a file nor a directory errors, exit 1."""
    code, _, err = _run(["list", str(tmp_path / "nope")])

    assert code == 1
    assert "directory or file not found" in err

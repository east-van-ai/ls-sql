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

from importlib import metadata
from io import StringIO
from unittest.mock import patch

from lssql.args import EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK, installed_version
from lssql.cli import main


def _run(argv, stdin_is_tty=False):
    """call main() with argv; return (exit_code, stdout, stderr).

    Two ways a code arrives. main() returns 0 and 1 itself, while argparse
    raises SystemExit(2) from inside parse_args() and never comes back. Both
    are caught here so a test can compare a code without caring which. See
    DESIGN.md, "main() returns a code, it does not exit".
    """

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
    ):
        try:
            code = main()
        except SystemExit as exit_call:
            code = exit_call.code
    return code, out.getvalue(), err.getvalue()


# -- the numbers behind the names --


def test_exit_codes_are_the_documented_numbers():
    """the three codes are 0, 1 and 2, whatever they are called.

    Every other assertion here compares against a name, so the names could all
    drift together and nothing would fail. This is the one place the numbers
    themselves are pinned. See DESIGN.md, "Exit codes".
    """
    assert (EXIT_OK, EXIT_ERROR, EXIT_ARGPARSE) == (0, 1, 2)


# -- --version answers wherever it lands --


def test_version_prints_the_installed_version():
    """`ls-sql --version` prints one line and exits 0, like the banner does.

    The 0 arrives as SystemExit from argparse's version action rather than as a
    return value, which _run() flattens. See DESIGN.md, "Exit codes".
    """
    code, out, _ = _run(["--version"])

    assert code == EXIT_OK
    assert out.strip().startswith("ls-sql ")
    assert len(out.strip().splitlines()) == 1


def test_version_answers_after_a_command_word():
    """a command word in front of it changes nothing, on purpose.

    The house rule keeps the flag off the subparsers so a command cannot answer
    it. ls-sql's parser is flat, and a version request means the same thing
    everywhere, so it is answered rather than scoped away. See DESIGN.md,
    "`--version` reads the installed metadata".
    """
    code, out, _ = _run(["harvest", ".", "--version"])

    assert code == EXIT_OK
    assert out.strip().startswith("ls-sql ")


def test_version_does_not_run_the_command(tmp_path):
    """parsing ends at the flag, so the command it was given never runs.

    The directory holds a file `list` would print a row for. Only the version
    line comes back.
    """
    (tmp_path / "photo.png").write_text("x")

    code, out, _ = _run(["list", str(tmp_path), "--version"])

    assert code == EXIT_OK
    assert "photo.png" not in out
    assert len(out.strip().splitlines()) == 1


def test_version_lookup_answers_when_nothing_is_installed():
    """a tree with no installed distribution gets an answer, not an exception.

    Patched rather than staged: a built tree keeps src/ls_sql.egg-info beside
    the package and metadata discovery reads it, so the branch is unreachable
    here on its own. It is reached on every command, not just this flag, since
    the lookup runs when the parser is built.
    """
    with patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError):
        assert installed_version() == "unknown (not installed)"


# -- the command word owns sys.argv[1] --


def test_command_must_come_first(tmp_path):
    """a flag before the command word is a usage error, not a reordering."""
    code, _, err = _run(["--commit", "harvest", str(tmp_path)])

    assert code == EXIT_ERROR
    assert "the command must come right after 'ls-sql'" in err
    assert "'--commit' first" in err


def test_unknown_command_is_an_argparse_error(tmp_path):
    """an unrecognised command word exits 2, argparse's own error."""
    code, _, err = _run(["badcmd", str(tmp_path)])

    assert code == EXIT_ARGPARSE
    assert "invalid choice" in err


def test_no_command_word_at_all(tmp_path):
    """`ls-sql .` is a usage error: there is no default command."""
    code, _, err = _run([str(tmp_path)])

    assert code == EXIT_ARGPARSE
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

    assert code == EXIT_ERROR
    assert "a path is required right after the command" in err


def test_path_right_after_the_command_is_accepted(tmp_path):
    """the documented order works."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    code, out, _ = _run(["harvest", str(tmp_path), "--commit"])

    assert code == EXIT_OK
    assert "committed" in out


def test_a_second_bare_word_is_an_ls_sql_error(tmp_path):
    """
    the slot holds one path, and a word behind it is ls-sql's own error.

    Argparse answers this with `unrecognized arguments`, exit 2, which reports
    the token without saying what the grammar wanted in its place. Reading the
    whole run of bare words ahead of the first flag is what lets ls-sql name it
    instead.
    """
    code, _, err = _run(["harvest", str(tmp_path), "extra"])

    assert code == EXIT_ERROR
    assert "harvest takes nothing after PATH: 'extra'" in err
    assert "Usage: ls-sql list|harvest|set|verify|reset PATH" in err


def test_missing_path_is_an_ls_sql_error(tmp_path):
    """
    a command with options but no path errors, exit 1, with compact USAGE.

    Bare `ls-sql harvest` is a help request; this is the case where the user
    asked for something specific and left the path out.
    """
    code, _, err = _run(["harvest", "--commit"])

    assert code == EXIT_ERROR
    assert "a path is required right after the command" in err
    assert "Usage: ls-sql list|harvest|set|verify|reset PATH" in err
    # compact USAGE only -- never the full argparse help dump
    assert "show this help message" not in err


def test_usage_continuation_aligns_under_the_first_line():
    """
    the second usage line is indented by exactly the width of "Usage: ".

    The prefix is printed in cli.py and the padding sits in args.py's USAGE, so
    nothing else pins the pairing. Every other assertion here matches a
    substring of the first line, which a prefix of a different width would
    still satisfy while the block came out crooked.
    """
    _, _, err = _run(["harvest", "no-such-path"])

    first, second = err.strip().splitlines()[-2:]
    indent = len("Usage: ")

    assert first.startswith("Usage: ls-sql")
    assert second[:indent].isspace()
    assert not second[indent].isspace()


def test_bare_command_is_a_help_request():
    """
    a command word and nothing else prints that command's help.

    Bare means literally bare. Once any other argument is present the user
    asked for something specific, and help text would hide the mistake.
    """
    code, out, _ = _run(["harvest"], stdin_is_tty=True)

    assert code == EXIT_OK
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

    assert code == EXIT_ERROR
    assert "--commit is not an option of 'list'" in err


def test_query_is_rejected_for_harvest(tmp_path):
    """--query belongs to list."""
    code, _, err = _run(["harvest", str(tmp_path), "--query", "SELECT * WHERE a='b'"])

    assert code == EXIT_ERROR
    assert "--query is not an option of 'harvest'" in err


def test_ext_is_rejected_for_set(tmp_path):
    """--ext belongs to harvest; set selects by path or hash."""
    code, _, err = _run(["set", str(tmp_path), "--tags", "ud:a=1", "--ext", "jpg"])

    assert code == EXIT_ERROR
    assert "--ext is not an option of 'set'" in err


def test_fh_is_rejected_for_verify(tmp_path):
    """--fh belongs to set."""
    code, _, err = _run(["verify", str(tmp_path), "--fh", "abc123"])

    assert code == EXIT_ERROR
    assert "--fh is not an option of 'verify'" in err


def test_set_requires_tags(tmp_path):
    """set without --tags has nothing to write."""
    code, _, err = _run(["set", str(tmp_path)])

    assert code == EXIT_ERROR
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
        assert code == EXIT_OK, f"{argv} failed: {err}"


# -- paths that do not exist --


def test_missing_directory_is_an_ls_sql_error(tmp_path):
    """a path that is neither a file nor a directory errors, exit 1."""
    code, _, err = _run(["list", str(tmp_path / "nope")])

    assert code == EXIT_ERROR
    assert "directory or file not found" in err

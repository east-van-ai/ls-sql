"""
tests pinning the command-word grammar itself.

ls-sql takes a command word in sys.argv[1] and a path in sys.argv[2]. The
command word is held there by the top-level parser, which knows no flag but -h
and --version. The path is read off sys.argv directly, because since Python
3.12 argparse back-fills a trailing optional positional from a token appearing
after any number of flags. Without these tests the accepted grammar could drift
away from the documented one and nothing would notice: the wrong command line
still parses, it just means something else.

Option B throughout: main() called directly with mocked sys.argv.
"""

import re
from importlib import metadata
from io import StringIO
from unittest.mock import patch

import pytest

from lssql.args import installed_version, version_line
from lssql.cli import COMMANDS, EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK, main


def _run(argv, stdin_is_tty=False):
    """call main() with argv; return (exit_code, stdout, stderr).

    Two ways a code arrives. main() returns 0 and 1 itself, while argparse
    raises SystemExit(2) from inside parse_args() and never comes back. Both
    are caught here so a test can compare a code without caring which.
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
    themselves are pinned.
    """
    assert (EXIT_OK, EXIT_ERROR, EXIT_ARGPARSE) == (0, 1, 2)


def test_every_parsed_command_has_an_action():
    """the command table and the parser's choices name the same commands.

    The subparsers decide what argparse accepts and COMMANDS decides what runs,
    so a word in one and not the other either never runs or never parses. The
    choices are read from argparse's own invalid-choice message.
    """
    _, _, err = _run(["badcmd", "."])
    choices = err.split("choose from ")[1].rstrip().rstrip(")").split(", ")

    assert set(COMMANDS) == set(choices)


# -- --version answers ahead of the command word --


def test_version_prints_the_installed_version():
    """`ls-sql --version` prints one line and exits 0, like the banner does.

    The 0 arrives as SystemExit from argparse's version action rather than as a
    return value, which _run() flattens. Neither spelling is documented, so
    these tests are the only record of the behaviour.
    """
    code, out, _ = _run(["--version"])

    assert code == EXIT_OK
    assert out.strip().startswith("ls-sql ")
    assert len(out.strip().splitlines()) == 1


def test_version_flag_after_a_command_word_is_unknown(tmp_path):
    """the flag lives on the top-level parser alone, so a command cannot answer it.

    The directory holds a file `list` would print a row for, and nothing comes
    back: the command does not run, and neither does the version action.
    """
    (tmp_path / "photo.png").write_text("x")

    code, out, err = _run(["list", str(tmp_path), "--version"])

    assert code == EXIT_ARGPARSE
    assert "unrecognized arguments: --version" in err
    assert out == ""


def test_version_lookup_answers_when_nothing_is_installed():
    """a tree with no installed distribution gets an answer, not an exception.

    Patched rather than staged: a built tree keeps src/ls_sql.egg-info beside
    the package and metadata discovery reads it, so the branch is unreachable
    here on its own. It is reached on every command, not just this flag, since
    the lookup runs when the parser is built.
    """
    with patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError):
        assert installed_version() == "unknown (not installed)"


# -- `version` is the second spelling, parsed like any command --


def test_version_command_word_prints_the_installed_version():
    """`ls-sql version` answers like the flag does, one line and exit 0."""
    code, out, _ = _run(["version"])

    assert code == EXIT_OK
    assert out.strip().startswith("ls-sql ")
    assert len(out.strip().splitlines()) == 1


def test_both_spellings_print_the_identical_line():
    """one helper builds the line, so the two cannot drift apart."""
    _, word_out, _ = _run(["version"])
    _, flag_out, _ = _run(["--version"])

    assert word_out.strip() == flag_out.strip()
    assert word_out.strip() == version_line()


def test_version_command_word_takes_nothing_after_it():
    """a bare word after `version` is a stray, exit 1, and it gets named."""
    code, _, err = _run(["version", "extra"])

    assert code == EXIT_ERROR
    assert "version takes nothing after it" in err
    assert "'extra'" in err
    assert err.splitlines()[-1] == "Usage: ls-sql version"
    # the stray names only the command typed, never the grammar of the others
    assert "harvest" not in err


def test_version_command_word_rejects_another_commands_flag():
    """`version` has no flags, so one belonging to another command is unknown."""
    code, _, err = _run(["version", "--commit"])

    assert code == EXIT_ARGPARSE
    assert "unrecognized arguments: --commit" in err


def test_version_command_word_rejects_a_flag_every_other_command_takes():
    """-R belongs to every command with a PATH, and version has none."""
    code, out, err = _run(["version", "-R"])

    assert code == EXIT_ARGPARSE
    assert "unrecognized arguments: -R" in err
    assert out == ""


def test_version_command_word_leaves_an_unknown_flag_to_argparse():
    """an unknown flag after `version` is argparse's to name, as after any command."""
    code, _, err = _run(["version", "--bogus"])

    assert code == EXIT_ARGPARSE
    assert "unrecognized arguments: --bogus" in err


def test_unknown_command_lists_version_among_the_choices():
    """an error naming the valid words is not advertising, so version is named.

    The banner is the `Usage:` the house rule closes, and it still leaves
    version out.
    """
    _, _, err = _run(["badcmd", "."])

    assert "version" in err.split("choose from")[1]


# -- the command word owns sys.argv[1] --


def test_command_must_come_first(tmp_path):
    """a flag before the command word is an error, not a reordering.

    The top-level parser knows no flag but -h and --version, so argparse
    rejects it, exit 2, and the command it came before never runs.
    """
    (tmp_path / "photo.jpg").write_text("fake image content")

    code, out, err = _run(["--commit", "harvest", str(tmp_path)])

    assert code == EXIT_ARGPARSE
    assert "unrecognized arguments: --commit" in err
    assert out == ""
    assert [p.name for p in tmp_path.iterdir()] == ["photo.jpg"]


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
    assert "ls-sql: harvest needs PATH" in err


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
    assert (
        err.splitlines()[-1]
        == "Usage: ls-sql harvest PATH [--commit] [--ext EXTS] [--max N] [-R] [--verbose]"
    )


def test_missing_path_is_an_ls_sql_error(tmp_path):
    """
    a command with options but no path errors, exit 1, with harvest's usage line.

    Bare `ls-sql harvest` is a help request; this is the case where the user
    asked for something specific and left the path out.
    """
    code, _, err = _run(["harvest", "--commit"])

    assert code == EXIT_ERROR
    assert "ls-sql: harvest needs PATH" in err
    assert (
        err.splitlines()[-1]
        == "Usage: ls-sql harvest PATH [--commit] [--ext EXTS] [--max N] [-R] [--verbose]"
    )
    # one usage line only -- never the full argparse help dump
    assert "show this help message" not in err


def test_a_grammar_error_prints_the_message_then_one_usage_line(tmp_path):
    """the message, then the failing command's usage line, and nothing else."""
    _, _, err = _run(["list", str(tmp_path), "--query", "nonsense"])

    # line[0] and line[1] form one line error message split by a new line '\n'.
    assert err.splitlines() == [
        "ls-sql: I'm sorry Dave, I can't run that query.",
        "  expected: SELECT * WHERE ...",
        "Usage: ls-sql list PATH [--query QUERY] [-R]",
    ]


def test_a_readiness_failure_prints_exactly_one_line():
    """the message only, no usage line, and nothing else."""
    _, _, err = _run(["harvest", "no-such-path"])

    assert err.splitlines() == ["ls-sql: directory or file not found: no-such-path"]


@pytest.mark.parametrize("command", list(COMMANDS))
def test_each_usage_line_names_its_own_options(command):
    """
    a command's usage line opens with its grammar and names its own flags.

    The drift guard: a flag added to a command's subparser fails here until the
    line gains it. The flags are read from argparse's own usage for the
    command, so the parser is the one source. --dry-run is left off every line,
    since it restates the default.
    """
    usage = COMMANDS[command].usage
    _, out, _ = _run([command, "-h"])
    flags = set(re.findall(r"\[(-[-\w]+)", out.split("\n\n")[0])) - {"-h", "--dry-run"}

    assert usage.startswith(" ".join(["ls-sql", command, *COMMANDS[command].slots]))
    assert "\n" not in usage
    for flag in flags:
        assert flag in usage


def test_an_unparseable_query_prints_the_list_usage(tmp_path):
    """the query error comes from inside list, and still ends in list's line."""
    code, _, err = _run(["list", str(tmp_path), "--query", "nonsense"])

    assert code == EXIT_ERROR
    assert err.splitlines()[-1] == "Usage: ls-sql list PATH [--query QUERY] [-R]"


def test_an_unmatched_fh_prints_the_set_usage(tmp_path):
    """the --fh error comes from inside set, and still ends in set's line."""
    (tmp_path / "photo.jpg").write_text("fake image content")

    code, _, err = _run(["set", str(tmp_path), "--tags", "ud:a=1", "--fh", "0000"])

    assert code == EXIT_ERROR
    assert "no file matched --fh: 0000" in err
    assert err.splitlines()[-1] == (
        "Usage: ls-sql set PATH --tags TAGS [--fh HASHES] [--commit] [-R] [--verbose]"
    )


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


@pytest.mark.parametrize(
    "argv, flag",
    [
        (["list", ".", "--commit"], "--commit"),
        (["harvest", ".", "--query", "SELECT * WHERE a='b'"], "--query"),
        (["set", ".", "--tags", "ud:a=1", "--ext", "jpg"], "--ext"),
        (["verify", ".", "--fh", "abc123"], "--fh"),
        (["list", ".", "--verbose"], "--verbose"),
    ],
)
def test_another_commands_flag_is_rejected(argv, flag):
    """
    each command's subparser knows only its own flags, so a foreign one is unknown.

    Rejected rather than ignored: `list PATH --commit` reads like a request to
    change files, and list never touches them. argparse names the flag, exit 2,
    and nothing reaches stdout.
    """
    code, out, err = _run(argv)

    assert code == EXIT_ARGPARSE
    assert f"unrecognized arguments: {flag}" in err
    assert out == ""


def test_set_requires_tags(tmp_path):
    """set without --tags has nothing to write."""
    code, _, err = _run(["set", str(tmp_path)])

    assert code == EXIT_ERROR
    assert "set requires --tags" in err


def test_shared_options_are_accepted_where_they_belong(tmp_path):
    """-R belongs to every command with a PATH, --verbose to all of them but list."""
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


# -- verify's exit 1 is a result, not an error --


def test_verify_changed_content_exits_1_with_nothing_on_stderr(tmp_path):
    """changed content: the summary on stdout, exit 1, and stderr stays empty."""
    (tmp_path / "a.txt").write_text("hello")
    _run(["harvest", str(tmp_path), "--commit", "--ext", "txt"])
    for harvested in tmp_path.iterdir():
        harvested.write_text("hello, changed")

    code, out, err = _run(["verify", str(tmp_path)])

    assert code == EXIT_ERROR
    assert "1 changed" in out
    assert err == ""


# -- help comes from argparse, every command listed --


def test_top_level_help_lists_every_command_version_included():
    """`ls-sql -h` names each command beside its help, version as well.

    It already lists --version under options, and the rule against advertising
    covers the banner and the docs, not argparse's own help.
    """
    code, out, _ = _run(["-h"])

    assert code == EXIT_OK
    for command in COMMANDS:
        assert f"    {command} " in out
    assert "version   Print the installed version and exit." in out


# -- main() takes the command line as a list --


def test_main_reads_argv_when_given(tmp_path):
    """a list passed to main() is the command line, sys.argv left untouched."""
    missing = str(tmp_path / "nope")

    with patch("sys.stderr", new_callable=StringIO) as err:
        code = main(["list", missing])

    assert code == EXIT_ERROR
    assert err.getvalue() == f"ls-sql: directory or file not found: {missing}\n"

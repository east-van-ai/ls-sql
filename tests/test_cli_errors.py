"""
tests pinning the raise-and-catch idiom at the CLI boundary.

Every other CLI test calls main(), which catches UsageError and ReadinessError
and turns them into ls-sql's error output. That makes them blind to how the
message got there: a command module going back to printing its own "ls-sql: "
line and returning EXIT_ERROR would leave them all green.

These call the command functions directly, so they assert the idiom rather than
the output. The message carries no "ls-sql: " prefix, because usage_error() and
readiness_error() are what supply it.
"""

import pytest

from lssql import cli_harvest, cli_list, cli_set, cli_verify
from lssql.args import build_parser
from lssql.errors import ReadinessError, UsageError


def _args(*tokens):
    """parse tokens with the real parser, so run() gets the namespace main() builds."""
    return build_parser().parse_args(list(tokens))


def test_list_raises_on_unparseable_query(tmp_path):
    """an unparseable --query raises rather than printing and returning."""
    (tmp_path / "a.jpg").touch()

    with pytest.raises(UsageError) as caught:
        cli_list.run(str(tmp_path), _args("list", "--query", "nonsense"))

    assert not str(caught.value).startswith("ls-sql:")


def test_set_raises_when_an_fh_prefix_matches_nothing(tmp_path):
    """an --fh prefix matching no file raises and names the prefix."""
    (tmp_path / "a.jpg").touch()

    with pytest.raises(UsageError) as caught:
        cli_set.run(str(tmp_path), _args("set", "--tags", "ud:a=1", "--fh", "00000000"))

    message = str(caught.value)
    assert "00000000" in message
    assert not message.startswith("ls-sql:")


def test_set_raises_without_tags(tmp_path):
    """set with no tags raises, carrying the message main() prints today."""
    (tmp_path / "a.jpg").touch()

    with pytest.raises(UsageError) as caught:
        cli_set.run(str(tmp_path), _args("set"))

    assert str(caught.value) == "set requires --tags."


def test_verify_raises_silently_after_the_summary(tmp_path, capsys):
    """changed content raises with no message, once the summary is printed."""
    (tmp_path / "a.txt").write_text("hello")
    cli_harvest.run(str(tmp_path), _args("harvest", "--commit", "--ext", "txt"))
    for harvested in tmp_path.iterdir():
        harvested.write_text("hello, changed")
    capsys.readouterr()

    with pytest.raises(ReadinessError) as caught:
        cli_verify.run(str(tmp_path), _args("verify"))

    assert str(caught.value) == ""
    assert "1 changed" in capsys.readouterr().out


def test_list_raises_readiness_on_a_missing_path(tmp_path):
    """a missing PATH is raised by the command, not reported by main()."""
    missing = str(tmp_path / "nope")

    with pytest.raises(ReadinessError) as caught:
        cli_list.run(missing, _args("list", missing))

    assert str(caught.value) == f"directory or file not found: {missing}"

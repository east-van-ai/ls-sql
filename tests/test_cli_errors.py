"""
tests pinning the raise-and-catch idiom at the CLI boundary.

Every other CLI test calls main(), which catches CliError and turns it into the
two-line error block. That makes them blind to how the message got there: a
command module going back to printing its own "ls-sql: " line and returning
EXIT_ERROR would leave them all green.

These call the command functions directly, so they assert the idiom rather than
the output. The message carries no "ls-sql: " prefix, because usage_error() is
what supplies it.
"""

import pytest

from lssql.args import CliError
from lssql.cli_list import run_list_mode
from lssql.cli_set import run_set_mode
from lssql.setter import parse_set_string


def test_list_raises_on_unparseable_query(tmp_path):
    """an unparseable --query raises rather than printing and returning."""
    (tmp_path / "a.jpg").touch()

    with pytest.raises(CliError) as caught:
        run_list_mode(str(tmp_path), query="nonsense")

    assert not str(caught.value).startswith("ls-sql:")


def test_set_raises_when_an_fh_prefix_matches_nothing(tmp_path):
    """an --fh prefix matching no file raises and names the prefix."""
    (tmp_path / "a.jpg").touch()
    ops, _ = parse_set_string("ud:a=1")

    with pytest.raises(CliError) as caught:
        run_set_mode(str(tmp_path), ops, commit=False, fh="00000000")

    message = str(caught.value)
    assert "00000000" in message
    assert not message.startswith("ls-sql:")

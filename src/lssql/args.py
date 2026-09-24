"""Argument parsing for ls-sql's CLI grammar."""

import argparse
from importlib import metadata

from lssql import cli_harvest, cli_list, cli_reset, cli_set, cli_verify

PROG = "ls-sql"


def installed_version():
    """
    return the version of the installed ls-sql distribution.

    The literal lives in pyproject.toml and reaches the CLI through the
    installed metadata, never through a second copy in the source.
    """
    try:
        return metadata.version("ls-sql")
    except metadata.PackageNotFoundError:
        return "unknown (not installed)"


def version_line():
    """
    return the program name and the installed version on one line.

    Both spellings print this, so the two cannot drift apart.
    """
    return f"{PROG} {installed_version()}"


def add_path(parser):
    """
    add the PATH positional a command acts on.

    nargs="?" because a bare command word is a help request, not an error.
    Registered so argparse consumes the token and prints [PATH]; the value it
    resolves is not the one main() acts on, which reads the slot off sys.argv.
    """
    parser.add_argument(
        "path",
        nargs="?",
        metavar="PATH",
        default=None,
        help="directory or file to act on; use . for the current directory",
    )


def add_recursive(parser):
    """add -R, which every command with a PATH takes."""
    parser.add_argument("-R", action="store_true", dest="recursive", help="recursive")


def add_verbose(parser):
    """add --verbose, for the commands that report files they skip."""
    parser.add_argument("--verbose", action="store_true", help="show skipped files")


def add_mode_flags(parser):
    """add --commit and --dry-run, for the commands that rename."""
    parser.add_argument("--commit", action="store_true", help="execute renames")
    parser.add_argument(
        "--dry-run", action="store_true", help="preview only, no changes"
    )


def add_command(subparsers, name, module):
    """add a command's subparser, described by its module's HELP, with its PATH."""
    parser = subparsers.add_parser(
        name, help=module.HELP, description=module.HELP, allow_abbrev=False
    )
    add_path(parser)
    add_recursive(parser)
    return parser


def build_parser():
    """
    build ls-sql's parser: one subparser per command, each with its own flags.

    A flag aimed at the wrong command is therefore argparse's unrecognized
    argument, exit 2, and so is any flag but -h and --version ahead of the
    command word, since the top-level parser knows no others.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="pipeable ls with SQL querying and metadata harvesting",
        # no abbreviations: --com must not silently mean --commit
        allow_abbrev=False,
    )

    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    version_help = "Print the installed version and exit."
    parser.add_argument(
        "--version", action="version", version=version_line(), help=version_help
    )
    subparsers.add_parser(
        "version", help=version_help, description=version_help, allow_abbrev=False
    )

    list_parser = add_command(subparsers, "list", cli_list)
    list_parser.add_argument(
        "--query",
        type=str,
        default="",
        metavar="QUERY",
        help="SQL-like query string: SELECT * WHERE key='value'",
    )

    harvest_parser = add_command(subparsers, "harvest", cli_harvest)
    add_verbose(harvest_parser)
    add_mode_flags(harvest_parser)
    harvest_parser.add_argument(
        "--ext",
        type=str,
        default="",
        metavar="EXTS",
        help="comma-separated extensions to harvest (e.g. jpg,png)",
    )
    harvest_parser.add_argument(
        "--max",
        type=int,
        default=0,
        dest="max_files",
        metavar="N",
        help="maximum number of files to harvest",
    )

    set_parser = add_command(subparsers, "set", cli_set)
    add_verbose(set_parser)
    add_mode_flags(set_parser)
    set_parser.add_argument(
        "--tags",
        type=str,
        default="",
        metavar="TAGS",
        help="caret-separated tag operations: ud:key=value^ud:other+=append",
    )
    set_parser.add_argument(
        "--fh",
        type=str,
        default=None,
        metavar="HASHES",
        help="comma-separated ls:fh prefixes to select files by content hash",
    )

    add_verbose(add_command(subparsers, "verify", cli_verify))

    reset_parser = add_command(subparsers, "reset", cli_reset)
    add_verbose(reset_parser)
    add_mode_flags(reset_parser)

    return parser

"""Argument parsing for ls-sql's CLI grammar."""

import argparse
from importlib import metadata

# Argparse hardcodes 2 in `ArgumentParser.error()`, which calls `sys.exit`
# itself, so EXIT_ARGPARSE never returns through main() and is only asserted
# against.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

PROG = "ls-sql"

USAGE = (
    "ls-sql list|harvest|set|verify|reset PATH [options]\n" "       ls <dir> | ls-sql"
)

# options each command accepts beyond the shared ones. Anything outside its
# command is an error, not something quietly ignored: `list PATH --commit`
# reads like a request to change files, and list never touches them.
#
# The keys are also the command vocabulary the parser accepts, so a new
# command cannot reach argparse without its option scope being decided.
COMMAND_OPTIONS = {
    "list": {"query"},
    "harvest": {"ext", "max_files", "commit", "dry_run"},
    "set": {"tags", "fh", "commit", "dry_run"},
    "verify": set(),
    "reset": {"commit", "dry_run"},
}

# argparse dest -> the spelling to put in an error message
OPTION_FLAGS = {
    "query": "--query",
    "ext": "--ext",
    "max_files": "--max",
    "tags": "--tags",
    "fh": "--fh",
    "commit": "--commit",
    "dry_run": "--dry-run",
}


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


def build_parser():
    """
    build ls-sql's single flat parser.

    Flat, not subparsers: the command and the path are ordinary positionals
    whose slots main() pins against sys.argv directly.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="pipeable ls with SQL querying and metadata harvesting",
        # no abbreviations: --com must not silently mean --commit
        allow_abbrev=False,
    )

    # Registered here rather than read off sys.argv: the action fires during
    # parsing, parser.parse_known_args(), ahead of the required-positional check,
    # which is what lets the flag answer with no command word in front of it.
    parser.add_argument(
        "--version",
        action="version",
        version=version_line(),
        help="print the installed version and exit",
    )

    parser.add_argument(
        "command",
        choices=list(COMMAND_OPTIONS),
        help="list | harvest | set | verify | reset",
    )

    # the path each command acts on -- second bare word, registered after the
    # command so it renders second in the usage line. nargs="?" because a bare
    # command word is a help request, not an error. Registered so argparse
    # consumes the token and prints [PATH]; the value it resolves is not the
    # one main() acts on.
    parser.add_argument(
        "path",
        nargs="?",
        metavar="PATH",
        default=None,
        help="directory or file to act on; use . for the current directory",
    )

    # shared options
    parser.add_argument("-R", action="store_true", dest="recursive", help="recursive")
    parser.add_argument("--verbose", action="store_true", help="show skipped files")
    parser.add_argument("--commit", action="store_true", help="execute renames")
    parser.add_argument(
        "--dry-run", action="store_true", help="preview only, no changes"
    )

    # scoped options -- accepted by the parser, then checked against
    # COMMAND_OPTIONS so a flag aimed at the wrong command is an error
    parser.add_argument(
        "--query",
        type=str,
        default="",
        metavar="QUERY",
        help="(list) SQL-like query string: SELECT * WHERE key='value'",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default="",
        metavar="EXTS",
        help="(harvest) comma-separated extensions to harvest (e.g. jpg,png)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        dest="max_files",
        metavar="N",
        help="(harvest) maximum number of files to harvest",
    )
    parser.add_argument(
        "--tags",
        type=str,
        default="",
        metavar="TAGS",
        help="(set) caret-separated tag operations: ud:key=value^ud:other+=append",
    )
    parser.add_argument(
        "--fh",
        type=str,
        default="",
        metavar="HASHES",
        help="(set) comma-separated ls:fh prefixes to select files by content hash",
    )

    return parser


def out_of_scope_option(args):
    """
    return the flag spelling of the first option not belonging to args.command.

    None when every option passed belongs to the command. Reporting is left to
    the caller, so every message ls-sql prints is written in one place.
    """
    allowed = COMMAND_OPTIONS[args.command]
    for dest, flag in OPTION_FLAGS.items():
        if dest in allowed:
            continue
        if getattr(args, dest):
            return flag
    return None

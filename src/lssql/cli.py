"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# lssql.cli - pipeable ls with SQL querying and metadata harvesting.
#
# Harvests file metadata (EXIF, ID3, image dimensions, ZIP contents)
# into the filename itself using the Hatfile convention:
# original^^^tag=value^tag=value^^^comment.ext
# No database -- the filesystem is the source of truth and the
# filename is the cache.
#
# Usage:
#    ls-sql <command> PATH [options]
#
#    LIST
#    ls-sql list PATH                                  print parsed rows
#    ls-sql list PATH --query "SELECT * WHERE k='v'"   filtered
#
#    HARVEST
#    ls-sql harvest PATH [--commit]                    metadata into names
#    ls-sql harvest PATH --commit --ext jpg,png --max 50
#
#    SET
#    ls-sql set PATH --tags "ud:key=value" [--commit]
#    ls-sql set PATH --tags "ud:key=value" --fh HASHES [--commit]
#
#    VERIFY
#    ls-sql verify PATH                                re-hash, compare ls:fh
#
#    RESET
#    ls-sql reset PATH [--commit]                      restore original names
#
#    PIPE
#    ls <dir> | ls-sql                                 passthrough parse
#
# The command word goes right after ls-sql, the path right after the
# command. Both positions are fixed; see DESIGN.md, "Positions are
# decided, not inferred".
#
# -R              recursive        --verbose        show skipped files
# --max N         harvest at most N files            (harvest)
# --ext EXTS      harvest only these extensions      (harvest)
# --tags TAGS     caret-separated tag operations     (set, required)
# --fh HASHES     select files by ls:fh hash prefix  (set)
# --query QUERY   SQL-like filter                    (list)
#
# Dry run by default: harvest/set/reset preview renames and change
# nothing. --commit is the single escalation that actually renames.
# --dry-run wins if both are passed.
#
# Exit codes:
#    0   success
#    1   ls-sql error; also verify when changed content is found
#    2   argument-parsing errors (unknown command, unknown flag)
#
# License: MIT
# ==============================================
"""

import argparse
import io
import os
import stat
import sys

from lssql import cli_harvest, cli_list, cli_reset, cli_set, cli_verify
from lssql.harvester_util import parse_ext_filter
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.setter import parse_set_string

USAGE = (
    "Usage: ls-sql list|harvest|set|verify|reset PATH [options]\n"
    "       ls <dir> | ls-sql"
)

_MODE_MODULES = {
    "list": cli_list,
    "harvest": cli_harvest,
    "set": cli_set,
    "verify": cli_verify,
    "reset": cli_reset,
}

# options each command accepts beyond the shared ones. Anything outside its
# command is an error, not something quietly ignored: `list PATH --commit`
# reads like a request to change files, and list never touches them.
_COMMAND_OPTIONS = {
    "list": {"query"},
    "harvest": {"ext", "max_files", "commit", "dry_run"},
    "set": {"tags", "fh", "commit", "dry_run"},
    "verify": set(),
    "reset": {"commit", "dry_run"},
}

# argparse dest -> the spelling to put in an error message
_OPTION_FLAGS = {
    "query": "--query",
    "ext": "--ext",
    "max_files": "--max",
    "tags": "--tags",
    "fh": "--fh",
    "commit": "--commit",
    "dry_run": "--dry-run",
}


def _die(message: str) -> None:
    """print an ls-sql error plus USAGE to stderr and exit 1."""
    print(f"ls-sql: {message}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(1)


def stdin_has_content() -> bool:
    """
    return True when stdin carries data: a pipe, a redirected file, or a socket.

    This is not the same question as isatty(). A terminal is not content, but
    neither is /dev/null, which is what cron, systemd, nohup, CI runners, and
    any subprocess with unattached stdin hand a process. `not isatty()` treats
    those as piped input, so a scheduled `ls-sql --harvest --commit` used to
    fall into passthrough mode, read nothing, rename nothing, and exit 0.

    Classifying by file type separates them; isatty() cannot:

    - S_ISFIFO -- a real pipe (`ls . | ls-sql`). Content.
    - S_ISREG  -- a redirect (`ls-sql < paths.txt`). Content.
    - S_ISSOCK -- socket. Content.
    - S_ISCHR  -- terminal or /dev/null. Not content.
    - stdin closed, or fileno()/fstat() failing. Not content.

    Note the direction: this is *narrower* than `not isatty()`, a strict subset
    of it. Only character devices leave the set. See DESIGN.md, "Piped is a
    file type, not the absence of a terminal".
    """
    stream = sys.stdin
    if stream is None:
        return False

    # A terminal is never piped content. Checking first also means a caller
    # that fakes a tty gets the answer it expects without a real file
    # descriptor behind it.
    try:
        if stream.isatty():
            return False
    except AttributeError, ValueError:
        return False

    try:
        mode = os.fstat(stream.fileno()).st_mode
    except AttributeError, OSError, ValueError, io.UnsupportedOperation:
        # No usable descriptor (closed, or replaced by an object without one).
        return False

    return stat.S_ISFIFO(mode) or stat.S_ISREG(mode) or stat.S_ISSOCK(mode)


def _build_parser():
    """
    build ls-sql's single flat parser.

    Flat, not subparsers: the command and the path are ordinary positionals
    whose slots main() pins against sys.argv directly. See DESIGN.md,
    "Positions are decided, not inferred".
    """
    parser = argparse.ArgumentParser(
        prog="ls-sql",
        description="pipeable ls with SQL querying and metadata harvesting",
        # no abbreviations: --com must not silently mean --commit
        allow_abbrev=False,
    )

    parser.add_argument(
        "command",
        choices=list(_MODE_MODULES),
        help="list | harvest | set | verify | reset",
    )

    # the path each command acts on -- second bare word, registered after the
    # command so it renders second in the usage line. nargs="?" because a bare
    # command word is a help request, not an error; main() enforces that the
    # path really is sys.argv[2].
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
    # _COMMAND_OPTIONS so a flag aimed at the wrong command is an error
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


def _reject_out_of_scope_options(args) -> None:
    """error on any scoped option that does not belong to args.command."""
    allowed = _COMMAND_OPTIONS[args.command]
    for dest, flag in _OPTION_FLAGS.items():
        if dest in allowed:
            continue
        if getattr(args, dest):
            _die(f"{flag} is not an option of '{args.command}'.")


def main():
    # A bare `ls-sql` is the only invocation that reads stdin. With a command
    # word present, stdin is not an input source at all and is left alone.
    #
    # Tempting to make a pipe plus a command a two-sources error, the way
    # every other house CLI treats a pipe plus a flag. It cannot work here.
    # An inherited pipe is indistinguishable from a deliberate one at the
    # file-descriptor level, so `printf x | sh -c 'ls-sql harvest .'` -- and
    # every ls-sql call inside a shell pipeline, Makefile recipe, or
    # subprocess -- would fail on a pipe the user never aimed at ls-sql.
    # Same trap as reading isatty() as "piped", one level up.
    if len(sys.argv) == 1:
        if stdin_has_content():
            for line in sys.stdin:
                path, filename = split_path(line.strip())
                if should_skip(filename):
                    continue
                parsed = parse_filename(filename)
                parsed["path"] = path
                print(build_file_path(parsed))
            sys.exit(0)

        # nothing piped, nothing asked for: print the banner, touch nothing
        print(__doc__)
        sys.exit(0)

    args = _build_parser().parse_args()

    # git-style: the command word must come right after 'ls-sql', not after
    # some flag that happens to parse. argparse has already resolved
    # args.command correctly -- it knows which raw token is the positional
    # regardless of interleaving -- so a flag came first exactly when that
    # token is not sys.argv[1]. A missing or misspelled command never reaches
    # here: it fails inside parse_args() with argparse's own error, exit 2.
    if sys.argv[1] != args.command:
        _die(f"the command must come right after 'ls-sql' (got {sys.argv[1]!r} first).")

    # ...and the path must come right after the command, in sys.argv[2].
    # Unlike the command word, argparse cannot be trusted to have resolved
    # this: since Python 3.12 it back-fills a trailing optional positional
    # from a token appearing after any number of flags, so
    # `ls-sql harvest --commit .` would parse happily with path set. That
    # would let the accepted grammar drift from the documented one, so the
    # slot is decided here on a single token. Anything argparse found
    # elsewhere is discarded; ls-sql does not go hunting for a path.
    path_token = sys.argv[2] if len(sys.argv) > 2 else None
    if path_token is None or path_token.startswith("-"):
        args.path = None

    # a command word and nothing else at all is a request for help, not an
    # error: same treatment as bare `ls-sql` above, one level down. Once any
    # other argument is present the user has asked for something specific,
    # and answering a wrong request with help would hide the mistake.
    #
    # No isatty() check. What was typed decides this, not how the process was
    # launched. Gating on the terminal made `ls-sql harvest` exit 0 from a
    # shell and 1 under nohup, cron, or an editor, on identical input.
    if args.path is None:
        if len(sys.argv) == 2:
            print(_MODE_MODULES[args.command].__doc__)
            sys.exit(0)
        _die(
            "a path is required right after the command; use '.' for the current directory."
        )

    if not (os.path.isdir(args.path) or os.path.isfile(args.path)):
        _die(f"directory or file not found: {args.path}")

    _reject_out_of_scope_options(args)

    commit = args.commit and not args.dry_run

    if args.command == "list":
        exit_code = cli_list.run_list_mode(
            args.path,
            query=args.query,
            recursive=args.recursive,
        )
        if exit_code:
            print(USAGE, file=sys.stderr)
        sys.exit(exit_code)

    if args.command == "harvest":
        cli_harvest.run_harvest_mode(
            args.path,
            commit=commit,
            recursive=args.recursive,
            max_files=args.max_files,
            allowed_exts=parse_ext_filter(args.ext),
            verbose=args.verbose,
        )
        sys.exit(0)

    if args.command == "set":
        if not args.tags:
            _die("set requires --tags.")

        ops, error = parse_set_string(args.tags)
        if error:
            _die(error)

        exit_code = cli_set.run_set_mode(
            args.path,
            ops,
            commit=commit,
            recursive=args.recursive,
            verbose=args.verbose,
            fh=args.fh,
        )
        if exit_code:
            print(USAGE, file=sys.stderr)
        sys.exit(exit_code)

    if args.command == "verify":
        # 1 if changed data is found; otherwise 0
        exit_code = cli_verify.run_verify_mode(
            args.path, recursive=args.recursive, verbose=args.verbose
        )
        sys.exit(exit_code)

    # reset
    cli_reset.run_reset_mode(
        args.path,
        commit=commit,
        recursive=args.recursive,
        verbose=args.verbose,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

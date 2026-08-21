"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# Harvests file metadata (EXIF, ID3, image dimensions, ZIP contents)
# into the filename itself using the Hatfile convention:
# original^^^ns:tag=value^ns:tag=value^^^comment.ext
# No database -- the filesystem is the source of truth and the
# filename is the cache.
#
# Usage:
#
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
#
#    0:     success
#    1:     ls-sql error; also verify when changed content is found
#    2:     argument-parsing errors (unknown command, unknown flag)
#
# License: MIT
# ==============================================
"""

import io
import os
import stat
import sys

from lssql import cli_harvest, cli_list, cli_reset, cli_set, cli_verify
from lssql.args import EXIT_ERROR, EXIT_OK, USAGE, build_parser, out_of_scope_option
from lssql.harvester_util import parse_ext_filter
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.setter import parse_set_string

_MODE_MODULES = {
    "list": cli_list,
    "harvest": cli_harvest,
    "set": cli_set,
    "verify": cli_verify,
    "reset": cli_reset,
}


def _usage_error(message: str) -> int:
    """
    print an ls-sql error plus USAGE to stderr, and return the error code.

    Every error prints both lines. See DESIGN.md, "Error style".
    """
    print(f"ls-sql: {message}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return EXIT_ERROR


def stdin_has_content() -> bool:
    """
    return True when stdin carries data: a pipe, a redirected file, or a socket.

    Not the question isatty() answers. /dev/null is no more content than a
    terminal is, and it is what cron, systemd, and any unattached subprocess
    hand a process. File type separates them; isatty() cannot. See DESIGN.md,
    "Piped is a file type, not the absence of a terminal".
    """
    stream = sys.stdin
    if stream is None:
        return False

    # A terminal is never content, and checking it first lets a caller fake a
    # tty without a real descriptor behind it.
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


def main() -> int:
    """
    read the command line, dispatch to a command, and return an exit code.

    Nothing here calls sys.exit(): the code travels back through the return,
    the way the cli_<command> modules already hand theirs up to this dispatch.
    See DESIGN.md, "main() returns a code, it does not exit".
    """
    # A bare `ls-sql` is the only invocation that reads stdin. With a command
    # word present stdin is left alone, and a pipe there is not an error: an
    # inherited pipe cannot be told from a deliberate one. See DESIGN.md,
    # "A pipe cannot be an error here".
    if len(sys.argv) == 1:
        if stdin_has_content():
            for line in sys.stdin:
                path, filename = split_path(line.strip())
                if should_skip(filename):
                    continue
                parsed = parse_filename(filename)
                parsed["path"] = path
                print(build_file_path(parsed))
            return EXIT_OK

        # nothing piped, nothing asked for: print the banner, touch nothing
        print(__doc__)
        return EXIT_OK

    args = build_parser().parse_args()

    # The command word must be sys.argv[1], so a flag came first exactly when
    # argparse's resolved command is some other token. A missing or misspelled
    # one never reaches here: parse_args() fails it with argparse's exit 2.
    if sys.argv[1] != args.command:
        return _usage_error(
            f"the command must come right after 'ls-sql' (got {sys.argv[1]!r} first)."
        )

    # ...and the path must be sys.argv[2], decided on that one token. What
    # argparse back-filled from later in the line is discarded. See DESIGN.md,
    # "Positions are decided, not inferred".
    path_token = sys.argv[2] if len(sys.argv) > 2 else None
    if path_token is None or path_token.startswith("-"):
        args.path = None

    # A command word and nothing else at all is a request for help. Once any
    # other token is present the user asked for something specific, and
    # answering with help would hide the mistake. No isatty() check: what was
    # typed decides, not how the process was launched.
    if args.path is None:
        if len(sys.argv) == 2:
            print(_MODE_MODULES[args.command].__doc__)
            return EXIT_OK
        return _usage_error(
            "a path is required right after the command; use '.' for the current directory."
        )

    if not (os.path.isdir(args.path) or os.path.isfile(args.path)):
        return _usage_error(f"directory or file not found: {args.path}")

    stray = out_of_scope_option(args)
    if stray:
        return _usage_error(f"{stray} is not an option of '{args.command}'.")

    commit = args.commit and not args.dry_run

    if args.command == "list":
        exit_code = cli_list.run_list_mode(
            args.path,
            query=args.query,
            recursive=args.recursive,
        )
        if exit_code:
            print(USAGE, file=sys.stderr)
        return exit_code

    if args.command == "harvest":
        cli_harvest.run_harvest_mode(
            args.path,
            commit=commit,
            recursive=args.recursive,
            max_files=args.max_files,
            allowed_exts=parse_ext_filter(args.ext),
            verbose=args.verbose,
        )
        return EXIT_OK

    if args.command == "set":
        if not args.tags:
            return _usage_error("set requires --tags.")

        ops, error = parse_set_string(args.tags)
        if error:
            return _usage_error(error)

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
        return exit_code

    if args.command == "verify":
        # 1 if changed data is found; otherwise 0
        return cli_verify.run_verify_mode(
            args.path, recursive=args.recursive, verbose=args.verbose
        )

    # reset
    cli_reset.run_reset_mode(
        args.path,
        commit=commit,
        recursive=args.recursive,
        verbose=args.verbose,
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

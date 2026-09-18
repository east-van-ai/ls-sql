"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai/ls-sql
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# No database -- the filesystem is the source of truth and the filename is the cache.
#
# Harvests file metadata (EXIF, ID3, image dimensions, ZIP contents)
# into the filename itself using the Hatfile convention:
# original^^^ns:tag=value^ns:tag=value^^^comment.ext
#
# Usage:
#
#   ls-sql <command> PATH [options]
#
#   LIST
#   ls-sql list PATH                                  print parsed rows
#   ls-sql list PATH --query "SELECT * WHERE k='v'"   filtered
#
#   HARVEST
#   ls-sql harvest PATH [--commit]                    metadata into names
#   ls-sql harvest PATH --commit --ext jpg,png --max 50
#
#   SET
#   ls-sql set PATH --tags "ud:key=value" [--commit]
#   ls-sql set PATH --tags "ud:key=value" --fh HASHES [--commit]
#
#   VERIFY
#   ls-sql verify PATH                                re-hash, compare ls:fh
#
#   RESET
#   ls-sql reset PATH [--commit]                      restore original names
#
#   PIPE
#   ls <dir> | ls-sql                                 passthrough parse
#
# The command word goes right after ls-sql, the path right after the
# command. Both positions are fixed.
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
#   0:  success
#   1:  ls-sql error; also verify when changed content is found
#   2:  argument-parsing errors (unknown command, unknown flag)
#
# License: MIT
# ==============================================
"""

import io
import os
import stat
import sys

from lssql import cli_harvest, cli_list, cli_reset, cli_set, cli_verify
from lssql.args import (
    EXIT_ERROR,
    EXIT_OK,
    CliError,
    build_parser,
    out_of_scope_option,
    version_line,
)
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

# version has no module to carry its usage line, so it sits beside the table
VERSION_USAGE = "ls-sql version"


def usage_error(usage: str, message: str) -> int:
    """Report any error, readiness failures included, with the matching usage."""
    print(f"ls-sql: {message}", file=sys.stderr)
    print(f"Usage: {usage}", file=sys.stderr)
    return EXIT_ERROR


def readiness_error(message: str) -> int:
    """Report what the run needed and did not find, with no usage line."""
    print(f"ls-sql: {message}", file=sys.stderr)
    return EXIT_ERROR


def stdin_has_content() -> bool:
    """
    return True when stdin carries data: a pipe, a redirected file, or a socket.

    Not the question isatty() answers. /dev/null is no more content than a
    terminal is, and it is what cron, systemd, and any unattached subprocess
    hand a process. File type separates them; isatty() cannot.
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


def leading_paths(tokens: list[str]) -> list[str]:
    """
    return the run of bare words ahead of the first flag.

    Collecting the whole run, not just the first word, is what lets a second
    bare word be reported rather than silently dropped.
    """
    paths = []
    for token in tokens:
        if token.startswith("-"):
            break
        paths.append(token)
    return paths


def main() -> int:
    """
    read the command line, dispatch to a command, and return an exit code.

    Nothing here calls sys.exit(): the code travels back through the return,
    the way the cli_<command> modules already hand theirs up to this dispatch.
    A command's own validation failure arrives as a CliError instead, so an
    exit code coming back is never an error.
    """
    # The only invocation that reads stdin.
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

        print(__doc__)
        return EXIT_OK

    # Ahead of the parser, like the banner above: a documentation request that
    # answers without a path. Routing it through COMMAND_OPTIONS would require a
    # PATH and would print the word in argparse's invalid-choice message.
    if sys.argv[1] == "version":
        if len(sys.argv) > 2:
            return usage_error(
                VERSION_USAGE, f"version takes nothing after it: {sys.argv[2]!r}"
            )
        print(version_line())
        return EXIT_OK

    parser = build_parser()
    args, extras = parser.parse_known_args()

    # An unknown flag is argparse's to name, so hand the line back to it.
    if any(extra.startswith("-") for extra in extras):
        parser.parse_args()

    # The command argparse resolved is still the one typed, even out of place.
    usage = _MODE_MODULES[args.command].USAGE

    # Both bare words are read off sys.argv, never taken from argparse: a flag
    # came first exactly when the resolved command is not sys.argv[1].
    if sys.argv[1] != args.command:
        return usage_error(
            usage,
            f"the command must come right after 'ls-sql' (got {sys.argv[1]!r} first).",
        )

    paths = leading_paths(sys.argv[2:])
    path = paths[0] if paths else None

    if len(paths) > 1:
        return usage_error(
            usage, f"{args.command} takes nothing after PATH: {paths[1]!r}"
        )

    # A command word and nothing else at all is a help request. Any other token
    # present means something specific was asked for.
    if path is None:
        if len(sys.argv) == 2:
            print(_MODE_MODULES[args.command].__doc__)
            return EXIT_OK
        return usage_error(
            usage,
            "a path is required right after the command; use '.' for the current directory.",
        )

    if not (os.path.isdir(path) or os.path.isfile(path)):
        return readiness_error(f"directory or file not found: {path}")

    stray = out_of_scope_option(args)
    if stray:
        return usage_error(usage, f"{stray} is not an option of '{args.command}'.")

    commit = args.commit and not args.dry_run

    # usage_error() writes the whole message, here and nowhere else.
    try:
        if args.command == "list":
            return cli_list.run_list_mode(
                path,
                query=args.query,
                recursive=args.recursive,
            )

        if args.command == "harvest":
            cli_harvest.run_harvest_mode(
                path,
                commit=commit,
                recursive=args.recursive,
                max_files=args.max_files,
                allowed_exts=parse_ext_filter(args.ext),
                verbose=args.verbose,
            )
            return EXIT_OK

        if args.command == "set":
            if not args.tags:
                return usage_error(usage, "set requires --tags.")

            ops, error = parse_set_string(args.tags)
            if error:
                return usage_error(usage, error)

            return cli_set.run_set_mode(
                path,
                ops,
                commit=commit,
                recursive=args.recursive,
                verbose=args.verbose,
                fh=args.fh,
            )

        if args.command == "verify":
            # 1 if changed data is found; otherwise 0
            return cli_verify.run_verify_mode(
                path, recursive=args.recursive, verbose=args.verbose
            )

        # reset
        cli_reset.run_reset_mode(
            path,
            commit=commit,
            recursive=args.recursive,
            verbose=args.verbose,
        )
        return EXIT_OK
    except CliError as error:
        return usage_error(usage, str(error))


if __name__ == "__main__":
    sys.exit(main())

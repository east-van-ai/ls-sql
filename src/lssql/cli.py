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
# -R              recursive
# --verbose       show skipped files                 (harvest, set, verify, reset)
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
from collections import namedtuple

from lssql import cli_harvest, cli_list, cli_reset, cli_set, cli_verify
from lssql.args import build_parser, version_line
from lssql.errors import ReadinessError, UsageError
from lssql.parser import build_file_path, parse_filename, should_skip, split_path

# Argparse hardcodes 2 in `ArgumentParser.error()`, which calls `sys.exit`
# itself, so EXIT_ARGPARSE never returns through main() and is only asserted
# against.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

__all__ = ["EXIT_ARGPARSE", "EXIT_ERROR", "EXIT_OK", "main"]

Command = namedtuple("Command", "bare usage slots action")
"""
a command word's answer to being typed alone, its usage line, the path slots it
reads, and the action a full invocation runs.

The action takes the paths and the parsed args, returns nothing, and raises to
fail. For version, bare and action both read from version_line, since running
the command answers the bare word.
"""

COMMANDS = {
    "list": Command(
        lambda: cli_list.__doc__,
        cli_list.USAGE,
        cli_list.SLOTS,
        lambda paths, args: cli_list.run(*paths, args=args),
    ),
    "harvest": Command(
        lambda: cli_harvest.__doc__,
        cli_harvest.USAGE,
        cli_harvest.SLOTS,
        lambda paths, args: cli_harvest.run(*paths, args=args),
    ),
    "set": Command(
        lambda: cli_set.__doc__,
        cli_set.USAGE,
        cli_set.SLOTS,
        lambda paths, args: cli_set.run(*paths, args=args),
    ),
    "verify": Command(
        lambda: cli_verify.__doc__,
        cli_verify.USAGE,
        cli_verify.SLOTS,
        lambda paths, args: cli_verify.run(*paths, args=args),
    ),
    "reset": Command(
        lambda: cli_reset.__doc__,
        cli_reset.USAGE,
        cli_reset.SLOTS,
        lambda paths, args: cli_reset.run(*paths, args=args),
    ),
    "version": Command(
        version_line,
        "ls-sql version",
        (),
        lambda paths, args: print(version_line()),
    ),
}


def usage_error(usage: str, message: str) -> int:
    """Report a command line ls-sql could not use, with that command's usage."""
    sys.stdout.flush()
    print(f"ls-sql: {message}", file=sys.stderr)
    print(f"Usage: {usage}", file=sys.stderr)
    return EXIT_ERROR


def readiness_error(message: str) -> int:
    """
    Report what the run needed and did not find, with no usage line.

    An empty message prints nothing: the command has already said everything
    on stdout, and only the exit code is left to carry.
    """
    sys.stdout.flush()
    if message:
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


def pipe_through(lines) -> None:
    """
    print each piped line as the full path of its parsed Hatfile name.

    Piped mode, a bare ls-sql with content on stdin. It takes any iterable of
    lines rather than reading sys.stdin itself, so it runs without main().
    Hidden and extensionless files are skipped, as in every other mode.
    """
    for line in lines:
        path, filename = split_path(line.strip())
        if should_skip(filename):
            continue
        parsed = parse_filename(filename)
        parsed["path"] = path
        print(build_file_path(parsed))


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


def main(argv=None) -> int:
    """
    read the command line, dispatch to a command, and return an exit code.

    argv is the command line after the program name, sys.argv[1:] when left
    out, so a caller can pass a list without patching sys.argv.

    Nothing here calls sys.exit(): the code travels back through the return.
    A command returns nothing and raises to fail, so every exit code is
    decided here.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)

    # The only invocation that reads stdin.
    if not tokens and stdin_has_content():
        pipe_through(sys.stdin)
        return EXIT_OK

    if not tokens:
        print(__doc__)
        return EXIT_OK

    if len(tokens) == 1 and tokens[0] in COMMANDS:
        print(COMMANDS[tokens[0]].bare())
        return EXIT_OK

    parser = build_parser()
    args, extras = parser.parse_known_args(tokens)

    # An unknown flag is argparse's to name, so hand the line back to it.
    if any(extra.startswith("-") for extra in extras):
        parser.parse_args(tokens)

    command = COMMANDS[args.command]

    paths = leading_paths(tokens[1:])

    if len(paths) < len(command.slots):
        needed = " and ".join(command.slots)
        if len(command.slots) > 1:
            needed = f"both {needed}"
        return usage_error(command.usage, f"{args.command} needs {needed}")

    if len(paths) > len(command.slots):
        stray = paths[len(command.slots)]
        last = command.slots[-1] if command.slots else "it"
        return usage_error(
            command.usage, f"{args.command} takes nothing after {last}: {stray!r}"
        )

    try:
        command.action(paths, args)
    except UsageError as error:
        return usage_error(command.usage, str(error))
    except ReadinessError as error:
        return readiness_error(str(error))

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

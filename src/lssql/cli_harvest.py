"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql harvest ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/ls-sql
#
# Read file metadata and encode it into the filename.
#
# Usage:
#
#   ls-sql harvest PATH                       preview renames, change nothing
#   ls-sql harvest PATH --commit              execute renames
#   ls-sql harvest PATH --commit -R           recurse into subdirectories
#   ls-sql harvest PATH --commit --ext jpg,png  only these extensions
#   ls-sql harvest PATH --commit --max 50     stop after N files
#
# Dry run by default. --commit is the single escalation that renames.
# Idempotent: already harvested files are skipped.
#
# Options: --commit, --dry-run, -R, --verbose, --ext, --max
"""

from lssql.harvester import harvest_directory, harvest_file
from lssql.harvester_util import parse_ext_filter
from lssql.shared import commit_requested, print_rename_results, require_path, resolve

HELP = "harvest metadata into filenames"
USAGE = "ls-sql harvest PATH [--commit] [--ext EXTS] [--max N] [-R] [--verbose]"
SLOTS = ("PATH",)


def run(target: str, args) -> None:
    """harvest metadata into filenames under target."""
    require_path(target)
    commit, recursive, verbose = commit_requested(args), args.recursive, args.verbose
    max_files, allowed_exts = args.max_files, parse_ext_filter(args.ext)
    results = resolve(
        target,
        lambda d, f: harvest_file(d, f, commit, allowed_exts),
        lambda t: harvest_directory(
            t,
            commit=commit,
            recursive=recursive,
            max_files=max_files,
            allowed_exts=allowed_exts,
        ),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

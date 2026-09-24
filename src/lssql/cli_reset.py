"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql reset ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/ls-sql
#
# Strip harvested tags and restore original filenames.
#
# Usage:
#
#   ls-sql reset PATH                preview the strip, change nothing
#   ls-sql reset PATH --commit       restore original filenames
#   ls-sql reset PATH --commit -R    recurse into subdirectories
#
# Everything between the first and second ^^^ goes. The human comment right
# of the second ^^^ is preserved, and the original filename left of the first
# ^^^ was never modified, so this is lossless.
#
# Dry run by default. --commit is the single escalation that renames.
#
# Options: --commit, --dry-run, -R, --verbose
"""

from lssql.harvester import remove_tags_from_directory, remove_tags_from_filename_commit
from lssql.shared import commit_requested, print_rename_results, require_path, resolve

HELP = "restore original filenames"
USAGE = "ls-sql reset PATH [--commit] [-R] [--verbose]"
SLOTS = ("PATH",)


def run(target: str, args) -> None:
    """strip all harvested tags from filenames under target."""
    require_path(target)
    commit, recursive, verbose = commit_requested(args), args.recursive, args.verbose
    results = resolve(
        target,
        lambda d, f: remove_tags_from_filename_commit(d, f, commit),
        lambda t: remove_tags_from_directory(t, commit=commit, recursive=recursive),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

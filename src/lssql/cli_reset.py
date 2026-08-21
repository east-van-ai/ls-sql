"""
ls-sql reset -- strip harvested tags and restore original filenames.

Usage:
   ls-sql reset PATH                preview the strip, change nothing
   ls-sql reset PATH --commit       restore original filenames
   ls-sql reset PATH --commit -R    recurse into subdirectories

Everything between the first and second ^^^ goes. The human comment right
of the second ^^^ is preserved, and the original filename left of the first
^^^ was never modified, so this is lossless.

Dry run by default. --commit is the single escalation that renames.

Options: --commit, --dry-run, -R, --verbose
"""

from lssql.harvester import remove_tags_from_directory, remove_tags_from_filename_commit
from lssql.shared import print_rename_results, resolve


def run_reset_mode(
    target: str, commit: bool, recursive: bool, verbose: bool = False
) -> None:
    """strip all harvested tags from filenames under target."""
    results = resolve(
        target,
        lambda d, f: remove_tags_from_filename_commit(d, f, commit),
        lambda t: remove_tags_from_directory(t, commit=commit, recursive=recursive),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

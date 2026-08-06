# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================

"""
ls-sql harvest -- read file metadata and encode it into the filename.

Usage:
   ls-sql harvest PATH                       preview renames, change nothing
   ls-sql harvest PATH --commit              execute renames
   ls-sql harvest PATH --commit -R           recurse into subdirectories
   ls-sql harvest PATH --commit --ext jpg,png  only these extensions
   ls-sql harvest PATH --commit --max 50     stop after N files

Dry run by default. --commit is the single escalation that renames.
Idempotent: already harvested files are skipped.

Options: --commit, --dry-run, -R, --verbose, --ext, --max
"""

from lssql.cli_util import print_rename_results, resolve
from lssql.harvester import harvest_directory, harvest_file


def run_harvest_mode(
    target: str,
    commit: bool,
    recursive: bool,
    max_files: int = 0,
    allowed_exts: set | None = None,
    verbose: bool = False,
) -> None:
    """harvest metadata into filenames under target."""
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

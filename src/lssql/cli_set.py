# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================

"""
ls-sql set -- write user-defined tags into filenames.

Usage:
   ls-sql set PATH --tags "ud:key=value"
   ls-sql set PATH --tags "ud:a=1^ud:b=2" --commit
   ls-sql set PATH --tags "ud:trip=london" -R --commit
   ls-sql set PATH --tags "ud:album=x" --fh ab2c3d,9fs7g1 --commit

Operators: = overwrite, += append, -= remove a value, == delete the tag.
Multiple operations are caret-separated, same as the filename format.

Un-harvested files are harvested first, silently. ls:fh is protected and
silently skipped. Writes to any 2-letter namespace other than ud: are
rejected, since those belong to the built-in harvesters.

Dry run by default. --commit is the single escalation that renames.

Options: --tags (required), --fh, --commit, --dry-run, -R, --verbose
"""

import sys

from lssql.cli_util import print_rename_results, resolve
from lssql.scanner import scan_directory
from lssql.setter import set_file, set_tags_directory


def run_set_mode(
    target: str,
    ops: list[dict],
    commit: bool,
    recursive: bool = False,
    verbose: bool = False,
    fh: str = "",
) -> int:
    """
    target is either a file path or a directory path.
    """
    if fh:
        # --fh mode: scan directory, match by hash, apply ops
        hashes = {h.strip() for h in fh.replace(",", ";").split(";")}
        rows = scan_directory(target, recursive=recursive)
        targets = [
            r
            for r in rows
            if r.get("tags", {}).get("ls:fh", "")[: len(next(iter(hashes)))] in hashes
        ]
        if not targets:
            print("ls-sql: no files matched --fh hashes", file=sys.stderr)
            return 1

        results = [set_file(r["path"], r["filename"], ops, commit) for r in targets]
        print_rename_results(
            results, recursive=recursive, verbose=verbose, commit=commit
        )

        return 0

    results = resolve(
        target,
        lambda d, f: set_file(d, f, ops, commit),
        lambda t: set_tags_directory(t, ops, commit, recursive=recursive),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

    return 0

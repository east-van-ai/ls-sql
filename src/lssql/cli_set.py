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

--fh takes comma-separated ls:fh prefixes of any length. A file matches when
its hash starts with one of them. A prefix that matches nothing stops the run
and is named, and no file is renamed.

Dry run by default. --commit is the single escalation that renames.

Options: --tags (required), --fh, --commit, --dry-run, -R, --verbose
"""

import sys

from lssql.args import EXIT_ERROR, EXIT_OK
from lssql.scanner import scan_directory
from lssql.setter import set_file, set_tags_directory
from lssql.shared import print_rename_results, resolve


def row_fh(row: dict) -> str:
    """return the ls:fh value stored in a scanned row, or an empty string."""
    return row.get("tags", {}).get("ls:fh", "")


def parse_fh_prefixes(fh: str) -> list[str]:
    """
    split an --fh argument into hash prefixes, in the order they were typed.

    Order is kept so an error can name a miss where the user can find it, and
    duplicates are dropped so it cannot name the same one twice. An empty
    prefix would match every row, so it never survives the split.
    """
    prefixes = []
    for raw in fh.replace(",", ";").split(";"):
        prefix = raw.strip()
        if prefix and prefix not in prefixes:
            prefixes.append(prefix)
    return prefixes


def run_set_mode(
    target: str,
    ops: list[dict],
    commit: bool,
    recursive: bool = False,
    verbose: bool = False,
    fh: str = "",
) -> int:
    """
    apply tag operations to files under target, and return an exit code.

    target is a file path or a directory path. With --fh the directory is
    scanned and files are picked by ls:fh prefix instead, which is the one
    selection that does not follow the path. EXIT_ERROR when a prefix matched
    nothing; otherwise EXIT_OK, dry-run and commit alike.
    """
    if fh:
        prefixes = parse_fh_prefixes(fh)
        if not prefixes:
            print("ls-sql: --fh needs at least one hash prefix.", file=sys.stderr)
            return EXIT_ERROR

        rows = scan_directory(target, recursive=recursive)

        # Each prefix stands on its own: one that matches nothing stops the run
        # rather than letting its neighbours rename a partial batch.
        missing = [
            p for p in prefixes if not any(row_fh(r).startswith(p) for r in rows)
        ]
        if missing:
            print(
                f"ls-sql: no file matched --fh: {', '.join(missing)}", file=sys.stderr
            )
            return EXIT_ERROR

        targets = [r for r in rows if any(row_fh(r).startswith(p) for p in prefixes)]

        results = [set_file(r["path"], r["filename"], ops, commit) for r in targets]
        print_rename_results(
            results, recursive=recursive, verbose=verbose, commit=commit
        )

        return EXIT_OK

    results = resolve(
        target,
        lambda d, f: set_file(d, f, ops, commit),
        lambda t: set_tags_directory(t, ops, commit, recursive=recursive),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

    return EXIT_OK

"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql set ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/ls-sql
#
# Write user-defined tags into filenames. Un-harvested files are harvested
# first, silently. ls:fh is protected and silently skipped. Writes to any
# 2-letter namespace other than ud: are rejected, since those belong to the
# built-in harvesters.
#
# Usage:
#
#   ls-sql set PATH --tags "ud:key=value"
#   ls-sql set PATH --tags "ud:a=1^ud:b=2" --commit
#   ls-sql set PATH --tags "ud:trip=london" -R --commit
#   ls-sql set PATH --tags "ud:album=x" --fh ab2c3d,9fs7g1 --commit
#
# Operators: = overwrite, += append, -= remove a value, == delete the tag.
# Multiple operations are caret-separated, same as the filename format.
#
# --fh takes comma-separated ls:fh prefixes of any length. A file matches when
# its hash starts with one of them. A prefix that matches nothing stops the run
# and is named, and no file is renamed.
#
# Dry run by default. --commit is the single escalation that renames.
#
# Options: --tags (required), --fh, --commit, --dry-run, -R, --verbose
"""

from lssql.errors import UsageError
from lssql.scanner import scan_directory
from lssql.setter import parse_set_string, set_file, set_tags_directory
from lssql.shared import commit_requested, print_rename_results, require_path, resolve

HELP = "write user-defined tags into filenames"
USAGE = "ls-sql set PATH --tags TAGS [--fh HASHES] [--commit] [-R] [--verbose]"
SLOTS = ("PATH",)


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


def run(target: str, args) -> None:
    """
    apply the tag operations in --tags to files under target.

    target is a file path or a directory path. With --fh the directory is
    scanned and files are picked by ls:fh prefix instead, which is the one
    selection that does not follow the path. Missing or unparseable tags, and
    an --fh that is empty or has a prefix matching nothing, raise UsageError.
    """
    require_path(target)
    tags, fh, commit = args.tags, args.fh, commit_requested(args)
    recursive, verbose = args.recursive, args.verbose

    if not tags:
        raise UsageError("set requires --tags.")

    ops, error = parse_set_string(tags)
    if error:
        raise UsageError(error)

    if fh is not None:
        prefixes = parse_fh_prefixes(fh)
        if not prefixes:
            raise UsageError("--fh needs at least one hash prefix.")

        rows = scan_directory(target, recursive=recursive)

        # Each prefix stands on its own: one that matches nothing stops the run
        # rather than letting its neighbours rename a partial batch.
        missing = [
            p for p in prefixes if not any(row_fh(r).startswith(p) for r in rows)
        ]
        if missing:
            raise UsageError(f"no file matched --fh: {', '.join(missing)}")

        targets = [r for r in rows if any(row_fh(r).startswith(p) for p in prefixes)]

        results = [set_file(r["path"], r["filename"], ops, commit) for r in targets]
        print_rename_results(
            results, recursive=recursive, verbose=verbose, commit=commit
        )
        return

    results = resolve(
        target,
        lambda d, f: set_file(d, f, ops, commit),
        lambda t: set_tags_directory(t, ops, commit, recursive=recursive),
    )

    print_rename_results(results, recursive=recursive, verbose=verbose, commit=commit)

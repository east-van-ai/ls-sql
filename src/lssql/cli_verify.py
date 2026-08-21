"""
ls-sql verify -- re-hash files and compare against ls:fh in the filename.

Usage:
   ls-sql verify PATH               summary only
   ls-sql verify PATH --verbose     per-file detail
   ls-sql verify PATH -R            recurse into subdirectories

Read-only. Never touches a file. Exit 1 when any content has changed, which
is a semantic result and not an error, so the message carries no ls-sql:
prefix. Files without ls:fh are skipped with a reason.

Options: -R, --verbose
"""

from lssql.args import EXIT_ERROR, EXIT_OK
from lssql.harvester import verify_directory, verify_file
from lssql.shared import resolve


def run_verify_mode(target: str, recursive: bool, verbose: bool) -> int:
    """
    returns exit code -- EXIT_OK(0) if all ok, EXIT_ERROR(1) if any changed.
    """

    results = resolve(
        target,
        verify_file,
        lambda t: verify_directory(t, recursive=recursive),
    )

    if verbose:
        for r in results:
            status = r["status"]
            directory = f"{r['directory']}/" if recursive else ""
            if status == "ok":
                print(f"       ok : {directory}{r['file']}")
            elif status == "changed":
                print(f"  CHANGED : {directory}{r['file']}")
                print(f"         expected : {r['stored']}")
                print(f"           actual : {r['actual']}")
            elif status == "skipped":
                print(f"  skipped : {directory}{r['file']}  ({r['reason']})")

    checked = sum(1 for r in results if r["status"] in ("ok", "changed"))
    changed = sum(1 for r in results if r["status"] == "changed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    print(f"\n{checked} file(s) checked, {changed} changed, {skipped} skipped")

    return EXIT_ERROR if changed else EXIT_OK

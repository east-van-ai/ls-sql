"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql verify ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/ls-sql
#
# Read-only. Re-hash files and compare against ls:fh in the filename. Never
# touches a file. Exit 1 when any content has changed, which is a semantic
# result and not an error. Files without ls:fh are skipped with a reason.
#
# Usage:
#
#   ls-sql verify PATH               summary only
#   ls-sql verify PATH --verbose     per-file detail
#   ls-sql verify PATH -R            recurse into subdirectories
#
# Options: -R, --verbose
"""

from lssql.errors import ReadinessError
from lssql.harvester import verify_directory, verify_file
from lssql.shared import require_path, resolve

HELP = "re-hash files and compare against ls:fh"
USAGE = "ls-sql verify PATH [-R] [--verbose]"
SLOTS = ("PATH",)


def run(target: str, args) -> None:
    """
    re-hash files under target and print how many changed.

    Changed content raises ReadinessError with no message once the summary is
    on stdout: main() turns it into exit 1 and prints nothing more, since the
    summary has already said it and the result is not an error.
    """
    require_path(target)
    recursive, verbose = args.recursive, args.verbose

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

    if changed:
        raise ReadinessError()

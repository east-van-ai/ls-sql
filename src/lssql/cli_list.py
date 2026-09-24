"""
# ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ls-sql list ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ ~~~
#
# https://github.com/east-van-ai/ls-sql
#
# Read filenames and print them, optionally filtered.
# The read-only mode, and the one that feeds a pipeline. Output is one full
# path per line with no summary, so it pipes into any Unix tool as-is.
#
# Usage:
#
#   ls-sql list PATH                                  every parsed row
#   ls-sql list PATH -R                               recurse
#   ls-sql list PATH --query "SELECT * WHERE k='v'"   filtered
#
# The query dialect supports =, CONTAINS, IS NULL, and IS NOT NULL. There is
# no FROM clause: there is only one thing to query.
#
# Options: --query, -R
"""

from lssql.errors import UsageError
from lssql.parser import build_file_path, parse_filename
from lssql.query import run_query
from lssql.scanner import scan_directory
from lssql.shared import require_path, resolve

HELP = "print parsed rows, optionally filtered"
USAGE = "ls-sql list PATH [--query QUERY] [-R]"
SLOTS = ("PATH",)


def run(target: str, args) -> None:
    """list parsed rows under target, filtered by --query when given."""
    require_path(target)
    query, recursive = args.query, args.recursive
    rows = resolve(
        target,
        lambda directory, filename: {**parse_filename(filename), "path": directory},
        lambda path: scan_directory(path, recursive=recursive),
    )

    if query:
        rows, error = run_query(query, rows)
        if error:
            raise UsageError(error)

    rows.sort(key=lambda d: d["filename"].lower())
    for row in rows:
        print(build_file_path(row))

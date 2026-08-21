"""
ls-sql list -- read filenames and print them, optionally filtered.

Usage:
   ls-sql list PATH                                  every parsed row
   ls-sql list PATH -R                               recurse
   ls-sql list PATH --query "SELECT * WHERE k='v'"   filtered

The read-only mode, and the one that feeds a pipeline. Output is one full
path per line with no summary, so it pipes into any Unix tool as-is.

The query dialect supports =, CONTAINS, IS NULL, and IS NOT NULL. There is
no FROM clause: there is only one thing to query.

Options: --query, -R
"""

import sys

from lssql.args import EXIT_ERROR, EXIT_OK
from lssql.parser import build_file_path, parse_filename
from lssql.query import run_query
from lssql.scanner import scan_directory
from lssql.shared import resolve


def run_list_mode(
    target: str,
    query: str = "",
    recursive: bool = False,
) -> int:
    """list parsed rows under target, filtered by query when given."""
    rows = resolve(
        target,
        lambda directory, filename: {**parse_filename(filename), "path": directory},
        lambda path: scan_directory(path, recursive=recursive),
    )

    if query:
        rows, error = run_query(query, rows)
        if error:
            print(f"ls-sql: {error}", file=sys.stderr)
            return EXIT_ERROR

    rows.sort(key=lambda d: d["filename"].lower())
    for row in rows:
        print(build_file_path(row))

    return EXIT_OK

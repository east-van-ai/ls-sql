# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================

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

import os
import sys

from lssql.parser import build_file_path, parse_filename, should_skip
from lssql.query import run_query
from lssql.scanner import scan_directory


def run_list_mode(
    target: str,
    query: str = "",
    recursive: bool = False,
) -> int:
    """list parsed rows under target, filtered by query when given."""
    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        if should_skip(filename):
            rows = []
        else:
            parsed = parse_filename(filename)
            parsed["path"] = directory
            rows = [parsed]
    else:
        rows = scan_directory(target, recursive=recursive)

    if query:
        matched, error = run_query(query, rows)
        if error:
            print(f"ls-sql: {error}", file=sys.stderr)
            return 1
        matched.sort(key=lambda d: d["filename"].lower())
        for row in matched:
            print(build_file_path(row))
    else:
        rows.sort(key=lambda d: d["filename"].lower())
        for row in rows:
            print(build_file_path(row))

    return 0

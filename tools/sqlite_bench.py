#!/usr/bin/env python3
"""
benchmark SQLite against the same question the filename scanners answer.

Walks a Hatfile corpus, loads one row per file into SQLite, then times the
lookup that `ls-sql list --query`, `find -name`, and `rg --files -g` all answer.
The point is the read number. The build is reported because the database has to
exist before it can be queried, not because it is the interesting part.

The schema is taken from the first file that parses, so this expects a uniform
corpus where every file carries the same tag keys. That is what the generators
in this directory produce.
"""

import argparse
import os
import sqlite3
import string
import sys
import tempfile
import time

from lssql.parser import parse_filename, should_skip

EXIT_OK = 0
EXIT_ERROR = 1

PROG = "sqlite_bench.py"
USAGE = f"{PROG} PATH TAG VALUE [--db FILE] [--keep]"

# Repeats to run each query. The best time is reported rather than the mean:
# the fastest run is the one least disturbed by other work on the machine.
REPEATS = 3

SAFE = set(string.ascii_letters + string.digits + "_")


def column_name(tag: str) -> str:
    """turn a tag key into a SQL column name: evai:fruit -> evai_fruit."""
    return "".join(character if character in SAFE else "_" for character in tag)


def usage_error(message: str) -> int:
    """print an error plus USAGE to stderr, and return the error code."""
    print(f"{PROG}: {message}", file=sys.stderr)
    print(f"Usage: {USAGE}", file=sys.stderr)
    return EXIT_ERROR


def human(count: int) -> str:
    """render a byte count in binary units."""
    size = float(count)
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} GB"


def walk(root: str):
    """yield (full_path, parsed_tags) for every non-skipped file under root."""
    for directory, _, filenames in os.walk(root):
        for filename in filenames:
            if should_skip(filename):
                continue
            yield os.path.join(directory, filename), parse_filename(filename)["tags"]


def first_schema(root: str) -> list[str] | None:
    """return the tag keys of the first parsed file, or None if there are none."""
    for _, tags in walk(root):
        if tags:
            return list(tags)
    return None


def load(connection, root: str, keys: list[str]) -> tuple[int, float]:
    """create the table and stream the corpus into it. returns (rows, seconds)."""
    columns = ", ".join(f'"{column_name(key)}" TEXT' for key in keys)
    connection.execute(f"CREATE TABLE files (path TEXT, {columns})")
    placeholders = ", ".join("?" * (len(keys) + 1))

    counted = 0

    def rows():
        nonlocal counted
        for path, tags in walk(root):
            counted += 1
            yield (path, *(tags.get(key) for key in keys))

    start = time.perf_counter()
    connection.executemany(f"INSERT INTO files VALUES ({placeholders})", rows())
    connection.commit()
    return counted, time.perf_counter() - start


def timed(connection, sql: str, parameters=()) -> tuple[float, int]:
    """run a query REPEATS times and return (best seconds, rows returned)."""
    best = float("inf")
    rows = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        rows = connection.execute(sql, parameters).fetchall()
        best = min(best, time.perf_counter() - start)
    return best, len(rows)


def build_parser() -> argparse.ArgumentParser:
    """build the argument parser."""
    parser = argparse.ArgumentParser(
        prog=PROG, description="time a SQLite lookup over a Hatfile corpus."
    )
    parser.add_argument("path", metavar="PATH", help="corpus directory to load")
    parser.add_argument("tag", metavar="TAG", help="tag key to query, e.g. evai:fruit")
    parser.add_argument("value", metavar="VALUE", help="value to match, e.g. apple")
    parser.add_argument("--db", help="where to write the database")
    parser.add_argument(
        "--keep", action="store_true", help="do not delete the database"
    )
    return parser


def main() -> int:
    """load the corpus into SQLite and time the lookup three ways."""
    args = build_parser().parse_args()

    if not os.path.isdir(args.path):
        return usage_error(f"not a directory: {args.path!r}")

    keys = first_schema(args.path)
    if keys is None:
        return usage_error(f"no tagged files under {args.path!r}")
    if args.tag not in keys:
        return usage_error(f"{args.tag!r} is not a tag here; found {', '.join(keys)}")

    database = args.db or os.path.join(tempfile.gettempdir(), "hatfile_bench.db")
    for leftover in (database, database + "-wal", database + "-shm"):
        if os.path.exists(leftover):
            os.remove(leftover)

    connection = sqlite3.connect(database)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=OFF")

    rows, build = load(connection, args.path, keys)
    column = column_name(args.tag)
    lookup = f'SELECT path FROM files WHERE "{column}" = ?'

    scan, matched = timed(connection, lookup, (args.value,))
    start = time.perf_counter()
    connection.execute(f'CREATE INDEX idx ON files("{column}")')
    connection.commit()
    indexing = time.perf_counter() - start
    indexed, _ = timed(connection, lookup, (args.value,))
    counting, _ = timed(
        connection, f'SELECT COUNT(*) FROM files WHERE "{column}" = ?', (args.value,)
    )
    connection.close()

    size = sum(
        os.path.getsize(part)
        for part in (database, database + "-wal", database + "-shm")
        if os.path.exists(part)
    )

    print(f"corpus     {args.path}")
    print(f"rows       {rows:,}")
    print(f"query      {args.tag} = {args.value}  ->  {matched:,} rows")
    print()
    print(f"indexed lookup     {indexed:8.3f} sec")
    print(f"unindexed scan     {scan:8.3f} sec")
    print(f"count only         {counting:8.3f} sec")
    print()
    print(f"load               {build:8.2f} sec")
    print(f"create index       {indexing:8.2f} sec")
    print(f"database           {human(size):>8}")

    if not args.keep:
        for part in (database, database + "-wal", database + "-shm"):
            if os.path.exists(part):
                os.remove(part)
    else:
        print(f"\nkept at {database}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

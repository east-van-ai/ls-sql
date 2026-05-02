import argparse
import os
import sys

from lssql.harvester import harvest_directory, remove_tags_from_directory
from lssql.harvester_util import parse_ext_filter
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.query import run_query
from lssql.scanner import scan_directory


def run_harvest_mode(
    path: str,
    commit: bool,
    recursive: bool,
    max_files: int = 0,
    allowed_exts: set = set(),
    verbose: bool = False,
) -> None:
    results = harvest_directory(
        path,
        commit=commit,
        recursive=recursive,
        max_files=max_files,
        allowed_exts=allowed_exts,
    )

    for r in results:
        status = r["status"]
        directory = f"{r['directory']}/" if recursive else ""
        if status in ("renamed", "dry-run"):
            print(f"  {status:>7} : {directory}{r['file']}")
            print(f"       -> : {directory}{r['new_name']}")
        elif status == "skipped" and verbose:
            print(f"  skipped : {directory}{r['file']}  ({r['reason']})")

    actioned = sum(1 for r in results if r["status"] in ("renamed", "dry-run"))
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")


def run_remove_mode(
    path: str, commit: bool, recursive: bool, verbose: bool = False
) -> None:
    results = remove_tags_from_directory(path, commit=commit, recursive=recursive)

    for r in results:
        status = r["status"]
        directory = f"{r['directory']}/" if recursive else ""
        if status in ("restored", "dry-run"):
            print(f"  {status:>8} : {directory}{r['file']}")
            print(f"        -> : {directory}{r['new_name']}")
        elif status == "skipped" and verbose:
            print(f"   skipped : {directory}{r['file']}  ({r['reason']})")

    actioned = sum(1 for r in results if r["status"] in ("restored", "dry-run"))
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")


def run_verify_mode(path: str, recursive: bool, verbose: bool) -> int:
    """
    returns exit code -- 0 if all ok, 1 if any changed.
    """
    from lssql.harvester import verify_directory

    results = verify_directory(path, recursive=recursive)

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

    return 1 if changed else 0


def main():
    # argparse only kicks in when there are actual args
    parser = argparse.ArgumentParser(
        prog="ls-sql",
        description="pipeable ls with SQL querying and metadata harvesting",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="",
        help="(required) target directory: . for the current directory",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        metavar="QUERY",
        help="SQL-like query string: SELECT * WHERE key='value'",
    )
    parser.add_argument("--harvest", action="store_true", help="harvest mode")
    parser.add_argument(
        "--remove-all-tags",
        action="store_true",
        help="strip all harvested tags, restore original filenames",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        metavar="N",
        help="maximum number of files to harvest",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default="",
        metavar="EXTS",
        help="comma-separated list of extensions to harvest (e.g. jpg,png)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="preview only, no changes"
    )
    parser.add_argument("--commit", action="store_true", help="execute renames")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="compare ls:fh in filename against current file content hash",
    )
    parser.add_argument("--verbose", action="store_true", help="show skipped files")
    parser.add_argument("-R", action="store_true", dest="recursive", help="recursive")

    # piped mode: ls data | python src/lssql/cli.py
    if not sys.stdin.isatty():
        for line in sys.stdin:
            path, filename = split_path(line.strip())
            if should_skip(filename):
                continue
            parsed = parse_filename(filename)
            parsed["path"] = path
            print(build_file_path(parsed))
        return

    args = parser.parse_args()

    # 'path' is a positional argument
    if not args.path:
        print("error: '--path' is required. use '.' for the current directory.\n")
        parser.print_help(sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.path):
        print(f"error: directory not found: {args.path}\n")
        parser.print_help(sys.stderr)
        sys.exit(1)

    # standalone remove all tags mode

    if args.remove_all_tags:
        commit = args.commit and not args.dry_run
        run_remove_mode(
            args.path, commit=commit, recursive=args.recursive, verbose=args.verbose
        )
        return

    # verify mode

    if args.verify:
        exit_code = run_verify_mode(
            args.path, recursive=args.recursive, verbose=args.verbose
        )
        sys.exit(exit_code)

    # standalone harvest mode

    if args.harvest:
        commit = args.commit and not args.dry_run
        allowed_exts = parse_ext_filter(args.ext)
        run_harvest_mode(
            args.path,
            commit=commit,
            recursive=args.recursive,
            max_files=args.max,
            allowed_exts=allowed_exts,
            verbose=args.verbose,
        )
        return

    # standalone query mode

    rows = scan_directory(args.path, recursive=args.recursive)

    if args.query:
        matched, error = run_query(args.query, rows)
        if error:
            print(error + "\n", file=sys.stderr)
            parser.print_help(sys.stderr)
            sys.exit(1)
        matched.sort(key=lambda d: d["filename"].lower())
        for row in matched:
            print(build_file_path(row))
    else:
        rows.sort(key=lambda d: d["filename"].lower())
        for row in rows:
            print(build_file_path(row))


if __name__ == "__main__":
    main()

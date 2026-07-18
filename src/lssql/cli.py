# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

import argparse
import os
import sys

from lssql.harvester import (
    harvest_directory,
    harvest_file,
    remove_tags_from_directory,
    remove_tags_from_filename_commit,
    verify_file,
    verify_directory,
)
from lssql.harvester_util import parse_ext_filter
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.query import run_query
from lssql.setter import parse_set_string, set_file, set_tags_directory
from lssql.scanner import scan_directory


def run_harvest_mode(
    target: str,
    commit: bool,
    recursive: bool,
    max_files: int = 0,
    allowed_exts: set = set(),
    verbose: bool = False,
) -> None:
    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        results = (
            []
            if should_skip(filename)
            else [harvest_file(directory, filename, commit, allowed_exts)]
        )
    else:
        results = harvest_directory(
            target,
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
    target: str, commit: bool, recursive: bool, verbose: bool = False
) -> None:
    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        results = (
            []
            if should_skip(filename)
            else [remove_tags_from_filename_commit(directory, filename, commit)]
        )
    else:
        results = remove_tags_from_directory(target, commit=commit, recursive=recursive)

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


def run_verify_mode(target: str, recursive: bool, verbose: bool) -> int:
    """
    returns exit code -- 0 if all ok, 1 if any changed.
    """

    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        results = [] if should_skip(filename) else [verify_file(directory, filename)]
    else:
        results = verify_directory(target, recursive=recursive)

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
            print("error: no files matched --fh hashes\n", file=sys.stderr)
            return 1

        results = [set_file(r["path"], r["filename"], ops, commit) for r in targets]
        # print results inline
        for res in results:
            status = res["status"]
            if status in ("updated", "dry-run"):
                print(f"  {status:>7} : {res['file']}")
                print(f"       -> : {res['new_name']}")
            elif status == "skipped" and verbose:
                print(f"  skipped : {res['file']}  ({res['reason']})")
        actioned = sum(1 for r in results if r["status"] in ("updated", "dry-run"))
        skipped = sum(1 for r in results if r["status"] == "skipped")
        mode_label = "committed" if commit else "dry-run"
        print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")
        if not commit:
            print("  (no files changed -- pass --commit to execute)")

        return 0

    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        results = (
            []
            if should_skip(filename)
            else [set_file(directory, filename, ops, commit)]
        )
    else:
        results = set_tags_directory(target, ops, commit, recursive=recursive)

    for r in results:
        status = r["status"]
        directory = f"{r['directory']}/" if recursive else ""
        if status in ("updated", "dry-run"):
            print(f"  {status:>7} : {directory}{r['file']}")
            print(f"       -> : {directory}{r['new_name']}")
        elif status == "skipped" and verbose:
            print(f"  skipped : {directory}{r['file']}  ({r['reason']})")

    actioned = sum(1 for r in results if r["status"] in ("updated", "dry-run"))
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")

    return 0


def run_query_mode(
    target: str,
    query: str = "",
    recursive: bool = False,
) -> int:
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
            print(error + "\n", file=sys.stderr)
            return 1
        matched.sort(key=lambda d: d["filename"].lower())
        for row in matched:
            print(build_file_path(row))
    else:
        rows.sort(key=lambda d: d["filename"].lower())
        for row in rows:
            print(build_file_path(row))

    return 0


def main():
    # argparse only kicks in when there are actual args
    parser = argparse.ArgumentParser(
        prog="ls-sql",
        description="pipeable ls with SQL querying and metadata harvesting",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="",
        help="(required) target directory or filename: . for the current directory",
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
    parser.add_argument(
        "--set",
        type=str,
        default="",
        metavar="TAGS",
        help="caret-separated tag operations: ud:key=value^ud:other+=append",
    )
    parser.add_argument(
        "--fh",
        type=str,
        default="",
        metavar="HASHES",
        help="comma-separated ls:fh prefixes to select files by content hash",
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
        sys.exit(0)

    args = parser.parse_args()

    # 'target' is a positional argument
    if not args.target:
        print(
            "error: 'target' is required. use '.' for the current directory.\n",
            file=sys.stderr,
        )
        parser.print_help(sys.stderr)
        sys.exit(1)

    if not (os.path.isdir(args.target) or os.path.isfile(args.target)):
        print(f"error: directory or file not found: {args.target}\n", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    # standalone remove all tags mode

    if args.remove_all_tags:
        commit = args.commit and not args.dry_run
        run_remove_mode(
            args.target,
            commit=commit,
            recursive=args.recursive,
            verbose=args.verbose,
        )
        sys.exit(0)

    # standalone verify mode

    if args.verify:
        # 1 if changed data is found; otherwise 0
        exit_code = run_verify_mode(
            args.target, recursive=args.recursive, verbose=args.verbose
        )
        sys.exit(exit_code)

    # standalone set mode

    if args.set:
        ops, error = parse_set_string(args.set)
        if error:
            print(error + "\n", file=sys.stderr)
            parser.print_help(sys.stderr)
            sys.exit(1)

        commit = args.commit and not args.dry_run
        exit_code = run_set_mode(
            args.target,
            ops,
            commit=commit,
            recursive=args.recursive,
            verbose=args.verbose,
            fh=args.fh,
        )
        if exit_code:
            parser.print_help(sys.stderr)
        sys.exit(exit_code)

    # standalone harvest mode

    if args.harvest:
        commit = args.commit and not args.dry_run
        allowed_exts = parse_ext_filter(args.ext)
        run_harvest_mode(
            args.target,
            commit=commit,
            recursive=args.recursive,
            max_files=args.max,
            allowed_exts=allowed_exts,
            verbose=args.verbose,
        )
        sys.exit(0)

    # standalone query mode

    exit_code = run_query_mode(
        args.target,
        query=args.query,
        recursive=args.recursive,
    )
    if exit_code:
        parser.print_help(sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

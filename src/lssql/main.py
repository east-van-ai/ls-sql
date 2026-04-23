import argparse
import os
import sys

from lssql.harvester import harvest_directory, remove_tags_from_directory
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.scanner import scan_directory


def run_harvest_mode(path: str, commit: bool, recursive: bool) -> None:
    results = harvest_directory(path, commit=commit, recursive=recursive)

    for r in results:
        status = r["status"]
        if status in ("renamed", "dry-run"):
            if recursive:
                print(f"  {status:>7} : {r['directory']}/{r['file']}")
                print(f"       -> : {r['directory']}/{r['new_name']}")
            else:
                print(f"  {status:>7} : {r['file']}")
                print(f"       -> : {r['new_name']}")
        elif status == "skipped":
            print(f"  skipped : {r['file']}  ({r['reason']})")

    total = len(results)
    actioned = sum(1 for r in results if r["status"] in ("renamed", "dry-run"))
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")


def run_remove_mode(path: str, commit: bool, recursive: bool) -> None:
    results = remove_tags_from_directory(path, commit=commit, recursive=recursive)

    for r in results:
        status = r["status"]
        if status in ("restored", "dry-run"):
            print(f"  {status:>7} : {r['file']}")
            print(f"        -> : {r['new_name']}")
        elif status == "skipped":
            print(f"  skipped : {r['file']}  ({r['reason']})")

    actioned = sum(1 for r in results if r["status"] in ("restored", "dry-run"))
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")


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
    parser.add_argument("--harvest", action="store_true", help="harvest mode")
    parser.add_argument(
        "--remove-all-tags",
        action="store_true",
        help="strip all harvested tags, restore original filenames",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="preview only, no changes"
    )
    parser.add_argument("--commit", action="store_true", help="execute renames")
    parser.add_argument("-R", action="store_true", dest="recursive", help="recursive")

    # piped mode: ls data | python src/lssql/main.py
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

    if args.recursive and not args.harvest:
        print(f"'-R' recursive is currently not supported in querying mode\n")
        parser.print_help(sys.stderr)
        sys.exit(1)

    # standalone remove all tags mode

    if args.remove_all_tags:
        commit = args.commit and not args.dry_run
        run_remove_mode(args.path, commit=commit, recursive=args.recursive)
        return

    # standalone harvest mode

    if args.harvest:
        commit = args.commit and not args.dry_run
        run_harvest_mode(args.path, commit=commit, recursive=args.recursive)
        return

    # standalone query mode

    rows = scan_directory(args.path)
    rows.sort(key=lambda d: d["filename"].lower())

    for row in rows:
        print(build_file_path(row))


if __name__ == "__main__":
    main()

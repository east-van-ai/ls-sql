import sys
from lssql.parser import build_file_path, parse_filename, should_skip, split_path
from lssql.scanner import scan_directory


def main():
    # piped mode: ls data | python src/lssql/main.py
    if not sys.stdin.isatty():
        for line in sys.stdin:
            path, filename = split_path(line.strip())
            if should_skip(filename):
                # None, '', '.', and '..' are skipped
                continue
            parsed = parse_filename(filename)
            parsed["path"] = path
            print(build_file_path(parsed))
        return

    # standalone mode: python src/lssql/main.py <directory>
    # sys.argv[0] => src/lssql/main.py
    # sys.argv[1] => <directory>
    if len(sys.argv) < 2:
        print("usage: python src/lssql/main.py <directory>", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]

    rows = scan_directory(directory)
    # alphabetical order like the default `ls` output
    rows.sort(key=lambda d: d["filename"].lower())

    for row in rows:
        print(build_file_path(row))


if __name__ == "__main__":
    main()

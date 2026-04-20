import sys
from lssql.parser import parse_filename, should_skip
from lssql.scanner import scan_directory


def main():
    # piped mode: ls data | python src/lssql/main.py
    if not sys.stdin.isatty():
        for line in sys.stdin:
            filename = line.strip()
            if should_skip(filename):
                # None, '', '.', and '..' are skipped
                continue
            parsed = parse_filename(filename)
            print(parsed)
        return

    # standalone mode: python src/lssql/main.py <directory>
    # sys.argv[0] => ../src/lssql/main.py
    # sys.argv[1] => <directory>
    if len(sys.argv) < 2:
        print("usage: python src/lssql/main.py <directory>", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]
    for row in scan_directory(directory):
        print(row)


if __name__ == "__main__":
    main()

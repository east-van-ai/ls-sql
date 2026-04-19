import sys
from lssql.parser import parse_filename, should_skip


def main():
    for line in sys.stdin:
        filename = line.strip()
        if should_skip(filename):
            # None, '', '.', and '..' are skipped
            continue

        parsed = parse_filename(filename)
        print(parsed)


if __name__ == "__main__":
    main()

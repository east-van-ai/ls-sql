#!/usr/bin/env python3
"""
generate the ls-sql test corpus, one .txt file per 5-digit hex code.

The code is both the file's index and its content. Each of the five digits
selects one word from one pool, so the filename and the two lines inside are a
pure function of the number. Nothing here is random and nothing is carried
between runs, which is what makes an interrupted run safe to resume: writing a
range again reproduces the same bytes, so ls:fh stays stable.
"""

import argparse
import os
import string
import sys

EXIT_OK = 0
EXIT_ERROR = 1

PROG = "test_data_generator.py"
USAGE = f"{PROG} PATH START END [--commit] [--force]"

# Five pools of sixteen, named for the sentence slot each one fills, and sorted
# alphabetically so a digit maps to a predictable word. 16 ** 5 == 1048576 ==
# 0xFFFFF + 1, so the five hex digits address exactly one word each with no
# remainder, and 00000..FFFFF covers every sentence exactly once. No word
# appears in two pools, so a bare filename search cannot confuse two slots.
# fmt: off
SUBJECTS = ["Bear", "Beaver", "Caribou", "Coyote", "Deer", "Eagle", "Elk", "Fox",
            "Lizard", "Marmot", "Moose", "Seal", "Snake", "Walrus", "Whale", "Wolf"]
VERBS = ["asked", "bought", "brought", "found", "gave", "got", "lent", "made",
         "offered", "promised", "sent", "showed", "sold", "taught", "told", "wrote"]
RECIPIENTS = ["alligator", "cat", "chicken", "cow", "dog", "goat", "horse", "lion",
              "llama", "monkey", "mouse", "ostrich", "pig", "rabbit", "sheep", "tiger"]
COLOURS = ["amber", "black", "blue", "brown", "gold", "green", "grey", "maroon",
           "navy", "pink", "purple", "red", "silver", "turquoise", "white", "yellow"]
FRUITS = ["apple", "banana", "berry", "cherry", "fig", "grape", "kiwi", "lemon",
          "lime", "mango", "melon", "orange", "papaya", "peach", "pear", "plum"]
# fmt: on

POOLS = (SUBJECTS, VERBS, RECIPIENTS, COLOURS, FRUITS)

CODE_WIDTH = 5

# Measured on APFS: a 4096-byte allocation block plus roughly 440 bytes of
# inode and directory record. A file this small never fills its block, so
# content length does not move this number -- file count is the only lever.
BYTES_ON_DISK = 4537

# The tree splits on the first two digits, so one leaf holds 16 ** 3 files.
FILES_PER_LEAF = 16**3

PROGRESS_EVERY = 4096


def words(code: str) -> list[str]:
    """return the five words a hex code selects, one from each pool."""
    return [pool[int(digit, 16)] for pool, digit in zip(POOLS, code)]


def sentence(code: str) -> str:
    """render a hex code as its five-word sentence."""
    return " ".join(words(code))


def contents(code: str) -> str:
    """render the two-line body of the file for a hex code."""
    return f"{code}\n{sentence(code)}\n"


def leaf_parts(code: str) -> tuple[str, str, str]:
    """
    return (subject, verb, filename) for a hex code.

    The first two digits name the two directory levels, which is why the tree
    splits 256 ways: sixteen subjects times sixteen verbs.
    """
    subject, verb = words(code)[:2]
    return subject, verb, f"{subject}-{code}.txt"


def code_error(text: str, label: str) -> str | None:
    """
    return an error message if text is not a hex code of the right width.

    The width is checked as well as the value. '0' and '00000' name the same
    file, but only one of them lines up under the eye beside its partner.
    """
    if len(text) != CODE_WIDTH:
        return f"{label} must be exactly {CODE_WIDTH} hex characters: {text!r}"
    if any(character not in string.hexdigits for character in text):
        return f"{label} is not hexadecimal: {text!r}"
    return None


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


def survey(root: str, start: int, end: int) -> tuple[int, int, int, int]:
    """
    return (missing, present, missing_bytes, total_bytes) for the range.

    Walks the same paths the write pass would, so the reported count is what
    would actually be written rather than the width of the range. That is what
    lets a resumed run say how much is left. The pools are ASCII, so the
    character count is the byte count.
    """
    missing = present = missing_bytes = total_bytes = 0
    for value in range(start, end + 1):
        code = f"{value:0{CODE_WIDTH}X}"
        subject, verb, name = leaf_parts(code)
        size = len(contents(code))
        total_bytes += size
        if os.path.exists(os.path.join(root, subject, verb, name)):
            present += 1
        else:
            missing += 1
            missing_bytes += size
    return missing, present, missing_bytes, total_bytes


def report(root: str, start: int, end: int, survey_result, force: bool) -> None:
    """print the counts and the size estimate for a run."""
    missing, present, missing_bytes, total_bytes = survey_result
    total = end - start + 1

    # A forced run rewrites what is already there, so it covers the whole range
    # rather than the gap the survey found.
    to_write, content_bytes = (
        (total, total_bytes) if force else (missing, missing_bytes)
    )

    # Leaves are decided by the first two digits, so the span in leaves is the
    # span of the range shifted down by the three digits below them.
    leaves = (end // FILES_PER_LEAF) - (start // FILES_PER_LEAF) + 1

    print(f"target     {root}")
    print(
        f"range      {start:0{CODE_WIDTH}X} to {end:0{CODE_WIDTH}X}  ({total:,} codes)"
    )
    print(f"leaf dirs  {leaves:,}")
    if present:
        print(f"present    {present:,}" + ("  (rewritten)" if force else "  (skipped)"))
    print(f"to write   {to_write:,} files")
    print(f"content    {human(content_bytes)}")
    print(f"on disk    {human(to_write * BYTES_ON_DISK)}")


def generate(root: str, start: int, end: int, force: bool) -> tuple[int, int]:
    """write the range, skipping files already present unless force is set."""
    written = skipped = 0
    made = set()

    for value in range(start, end + 1):
        code = f"{value:0{CODE_WIDTH}X}"
        subject, verb, name = leaf_parts(code)
        leaf = os.path.join(root, subject, verb)

        # One makedirs per leaf, not one per file. At a million files the
        # syscall would dominate the run.
        if leaf not in made:
            os.makedirs(leaf, exist_ok=True)
            made.add(leaf)

        target = os.path.join(leaf, name)
        if not force and os.path.exists(target):
            skipped += 1
            continue

        with open(target, "w", encoding="utf-8") as handle:
            handle.write(contents(code))
        written += 1

        if written % PROGRESS_EVERY == 0:
            print(f"  {written:,} written", flush=True)

    return written, skipped


def build_parser() -> argparse.ArgumentParser:
    """build the argument parser."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="generate the ls-sql test corpus, one .txt file per hex code.",
    )
    # All three positionals are required, so argparse cannot back-fill a
    # trailing one from a token after a flag. The hazard that makes cli.py read
    # its slots off sys.argv does not exist here.
    parser.add_argument("path", metavar="PATH", help="directory to fill")
    parser.add_argument(
        "start", metavar="START", help=f"first hex code, {CODE_WIDTH} characters"
    )
    parser.add_argument(
        "end", metavar="END", help=f"last hex code, {CODE_WIDTH} characters, inclusive"
    )
    parser.add_argument("--commit", action="store_true", help="write the files")
    parser.add_argument(
        "--force", action="store_true", help="rewrite files already present"
    )
    return parser


def main() -> int:
    """parse the command line, survey the range, and write it if asked."""
    args = build_parser().parse_args()

    for text, label in ((args.start, "START"), (args.end, "END")):
        message = code_error(text, label)
        if message:
            return usage_error(message)

    start, end = int(args.start, 16), int(args.end, 16)
    if start > end:
        return usage_error(f"START {args.start} is past END {args.end}")

    report(args.path, start, end, survey(args.path, start, end), args.force)

    if not args.commit:
        print("\ndry run. add --commit to write.")
        return EXIT_OK

    written, skipped = generate(args.path, start, end, args.force)
    print(f"\nwrote {written:,} files, skipped {skipped:,}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

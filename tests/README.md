# tests

## Test data

Some tests require real media files that are not committed to the repository.
Place them in `tests/data/` before running the full test suite.

| File                | Used by                  | Notes                        |
|---------------------|--------------------------|------------------------------|
| `sample.m4a`        | `test_harvester_au.py`   | any M4A file, 15sec is fine  |

### Why not committed?

Binary test files bloat the repository. A short real file is more reliable
than a synthetic one for format-sensitive libraries like mutagen.

### Getting a test file

Any M4A file works. The shortest one you have is fine.
iPhone voice memos are M4A by default -- a 15 second recording is plenty.
Rename it to match the filename in the table above and drop it in `tests/data/`.

### Skipping gracefully

Tests that depend on these files will skip automatically if the file is absent.
You will see `SKIPPED` in pytest output with a message pointing here.
No test will fail due to a missing data file.

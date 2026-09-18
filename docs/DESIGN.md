# ls-sql design & specification

What the tool builds and why. The command surface, the flags, and the exit
codes are in [CLI.md](CLI.md).

## Hatfile

A Hatfile is a plain filename that carries structured metadata.
No sidecar files. No database. No app required.

The metadata lives between `^^^` boundaries, visible to any file browser,
searchable by Spotlight, greppable from Terminal.

```text
IMAGE-1234567890^^^ls:hd=20260428^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:cam=canon-r5^^^2006-london-lunch-at-oxo.jpg
^-- original ---^^^--- structured metadata -------------------------------------------------^^^---- human comment -----^
```

Disposable and rebuildable. The file is the record.

See [HATFILE.md](HATFILE.md).

## ls-sql Architecture

Five commands, two halves.

```bash
ls-sql harvest .  # reads files, renames them
ls-sql set .      # renames
ls-sql reset .    # renames
ls-sql list .     # reads filenames, never touches a file
ls-sql verify .   # reads and re-hashes, never touches a file
```

Three commands rename, two never do. That distinction is absolute, and it is
the reason dry-run is the default on the first three and meaningless on the
other two.

The filesystem is the only source of truth. There is no database to maintain,
no cache to invalidate, no records to go stale. Everything ls-sql knows lives
in filenames.

## Filename specification

### Hatfile metadata and boundary

`^^^` marks the boundary between the original filename and Hatfile metadata.
This is the Hatfile standard. It is not configurable.

```text
{original_filename}^^^{Hatfile_metadata}^^^{human_comment}.{ext}
```

- Left of the first `^^^` sits the original filename, never modified.
- Between the boundaries sit the tagged key-value pairs.
- Right of the second `^^^` sits a free human comment, and it is optional.
- The trailing `^^^` is always present, even without a comment.
- Aim to keep the whole name under 200 characters.

### Tagged key-value format

All metadata uses `namespace:key=value` pairs separated by `^`. Order does not
matter. Missing fields are skipped cleanly.

```text
ls:hd=20260503^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:dto=2024:07:12
```

### Multi-value separator

Semicolon `;` separates the values inside one tag. Comma is allowed freely,
because artist names, album titles, and captions naturally contain commas.
Semicolon is rare enough in metadata to serve as a clean delimiter. Duplicate
values are dropped and the survivors are sorted alphabetically.

```text
ud:tags=foggy;london;sunny
au:al=Simon & Garfunkel, Greatest Hits    # comma in value, fine
```

### Character budget

```text
A1111 original:       ~19 chars     (e.g. 00234-1234567890.png)
Separator ^^^ x 2:      6 chars
Tagged metadata:      ~80 chars     (reasonable field set)
Human comment:        ~80 chars     remaining budget
Total target:        <200 chars     well within macOS 255 byte limit
```

## Tag namespaces

Namespaces keep tags organised and prevent collisions between sources.

```text
au:    audio metadata (MP3, AAC, FLAC, whatever comes next)
ex:    EXIF data
ls:    ls-sql native tags
sd:    Stable Diffusion / A1111 (reserved, not harvested)
ud:    user defined custom tags
zi:    zipfile info (.zip files)
```

### Namespace rules

2-letter namespaces are reserved for ls-sql built-in harvesters. They are short
because they appear in filenames and character budget matters.

- `ud:` is the blessed user namespace for simple custom tags.
- Use 1-letter or 3-letter+ namespaces for your own structured extensions
  (e.g. `myapp:key=value`).
- Use a 2-letter namespace and you are on your own, since harvest will overwrite
  it. `set` refuses the write, which is where the rule is enforced.

### Tag reference

ls-sql native tags. Every harvested file carries `ls:hd` and `ls:fh`; the
dimensions appear for images only.

```text
ls:hd    Harvest date (YYYYMMDD)
ls:fh    File content hash (16 chars SHA256, content fingerprint)
ls:dw    Image width
ls:dh    Image height
```

EXIF, read via `piexif` from JPG files. No extraction required.

```text
ex:dto   DateTimeOriginal (e.g. 2024:07:12)
ex:cam   Camera model, slugified (e.g. canon-r5)
ex:fl    Focal length (e.g. 50mm)
ex:ap    Aperture (e.g. f2.8)
ex:iso   ISO value
```

Audio, read via `mutagen`. ID3 and the equivalents in other containers.

```text
au:ar    Artist
au:al    Album
au:tt    Track title
au:tn    Track number
au:yr    Year
```

ZIP and CBZ. A container's metadata worth capturing is what is inside it, not
the compression. The format stores its central directory separately from the
compressed data, so the entry names are readable without decompression.

```text
zi:cnt    total entry count (files and directories, including dot entries)
zi:ext    content types, comma-separated extensions, no dots (e.g. jpg,png,txt)
          directories excluded -- extensions only make sense for files
zi:dot    dot entry count (files and directories starting with a dot)
          only present when > 0 -- presence alone is the signal
zi:dir    directory count -- explicit and implicit combined, deduplicated
          explicit: entries whose name ends with /
          implicit: parent path segments inferred from file entries
```

Directory entries are optional in the ZIP format, and many tools omit them and
write only file entries. Counting the implicit parents is what makes `zi:dir`
reflect the real structure. A ZIP holding thousands of empty explicit
directories and no files at all lands on the same count from the other side.

macOS resource forks, the `__MACOSX/` tree and the `._` sidecars, are filtered
out. They are implementation noise rather than content, and there is no flag to
keep them.

Stable Diffusion. The namespace is reserved and the names below are fixed, but
nothing harvests them. They are written down so the names are not reused.

```text
sd:mn    Model name          sd:sh    Schedule type
sd:mh    Model hash          sd:cfg   CFG scale
sd:sa    Sampler             sd:sd    Seed
sd:sp    Sampling steps      sd:la    LoRA
```

`ud:` is anything that does not overlap with the above.

### Note on name hash

There is no filename hash tag. You cannot take a hash of a filename that
already contains a hash. The result would never match anything on rebuild.
The file content hash (`ls:fh`) is the stable fingerprint. That is enough.

### Duplicate detection is a consequence, not a feature

`ls:fh` is the content fingerprint, so duplicates share a hash whatever they
are called. Nothing in the harvester knows about duplicates, and nothing needs
to:

```bash
ls-sql list . -R --query "SELECT * WHERE ls:fh IS NOT NULL" \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

### Albums are `ud:` tags

An album is a `ud:` tag applied consistently across files, and nothing else.
No separate data structure, no album record, no database. The album name is the
key and the value is a sequence number.

```text
IMG_4520^^^ex:dto=2006:03:15^ls:fh=9b1d4e72ac^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ex:dto=2006:04:10^ls:fh=c3f8a12b91^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ex:dto=2006:04:15^ls:fh=a3f2c8f91b^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
```

One file can belong to as many albums as it has tags. Albums carry no metadata
of their own, since the filename is the record. Sequence gaps are allowed,
because the order is explicit and human-controlled.

The same shape covers anything a checkbox list would cover. One key, several
values, no schema:

```text
roast-beef^^^ls:fh=9b1d4e72ac^ud:ingredients=beef;carrot;garlic^^^at-mrs-johnsons.jpg
carbonara^^^ls:fh=a3f2c8f91b^ud:ingredients=garlic;pepper;pork^^^italian-night.jpg
```

## Configuration

There is no configuration file. ls-sql runs on hardcoded defaults, and every
knob it has is a command-line flag.

- Harvest boundary: `^^^`, which is the Hatfile standard and not configurable
- Longest stem the harvester will touch: 80 characters
- Fields harvested: all available for the file type

## Edge cases

When in doubt, warn and skip. Never guess.

- **Malformed caret runs.** The stem is not a Hatfile. See below.
- **Stem longer than 80 characters.** The harvester reports the file as
  skipped and moves on, before any rename. See below.
- **File already harvested.** The harvester sees `^^^` and skips. Idempotent.
- **Duplicate files.** `ls:fh` catches identical content whatever the filename.

### What counts as a Hatfile stem

A stem is a Hatfile stem when every one of these holds:

- it splits into at most three parts on `^^^`
- the original part holds no `^`
- the tag part is empty, or splits on `^` into segments that are all non-empty
- the comment part, when present, holds no `^`

Anything else parses as a plain filename, and the write paths skip it.

The tag part needs a clause of its own because `^` is the tag delimiter there.
`ls:hd=20260503^ls:fh=03754271b00a0e1c` is well-formed. A leading caret is not,
because it opens an empty segment.

A run of six carets stays valid. That shape is `original^^^^^^comment`, a
harvested file with an empty tag section. A rule phrased as "every caret run is
exactly three" would reject it by accident.

The rule exists because splitting on `^^^` alone loses data. `str.split` is
greedy from the left, so an odd caret stays glued to the front of the next
field, and `0001-01234^^^^it-is-blue` reads as tags of `^it-is-blue`. That
parses as no tags at all, and `set` then overwrites the tag section and drops
the text:

```text
0001-01234^^^^it-is-blue.png
  -> 0001-01234^^^ud:colour=blue^^^.png
```

`it-is-blue` is gone, and `reset` cannot recover it. The filename is the only
store this project has, so a name it cannot read confidently is a name it must
not rewrite.

A tempting alternative is to treat any run of three or more carets as a
boundary and discard the extras. That guesses, and the guess deletes carets the
user typed.

### The only length rule is 80 characters on the stem

The harvester refuses any file whose stem is already 81 characters or longer.
The file is reported as skipped, with the measured length beside the limit, and
nothing is renamed.

The check sits on the stem rather than on the finished name because the stem is
the input. It is known before a single byte of metadata is read, so a file that
cannot fit its tags costs nothing to refuse, and the number in the message is
one the user can act on. Checking the result instead would mean building a name
in order to throw it away, and reporting a length the user has no direct handle
on.

The 200-character total is a target, not a ceiling. Nothing counts up to it,
and nothing counts up to the macOS limit of 255 bytes either. A stem inside the
cap can still produce a name past 200 if the tag set and the comment are both
generous. That is left to the user, who can see the result and shorten the
comment.

## Implementation

### Language

Python 3.14 or newer, the floor declared in `pyproject.toml`. Built as a
src-layout package and installed with `pipx` from the git repository.

### Key dependencies

```text
Pillow          image resolution extraction (JPG, PNG, GIF, WEBP)
piexif          EXIF reading for JPG
mutagen         ID3/MP3 metadata extraction
hashlib         SHA256 for file content hash (stdlib)
os.scandir()    fast directory traversal (stdlib)
```

No database dependency. No ORM. No migration files.

#### Dependencies are floors, not pins

`[project] dependencies` lists the three packages ls-sql imports, with lower
bounds and no upper caps. A floor is a claim the project can stand behind,
being the version ls-sql was last tested against. A cap would be a claim about
releases that do not exist yet, and that guess strands users on the day Pillow
ships a fine new version.

Exact pins carry a second cost. `pillow==12.2.0` is not a fact about ls-sql. It
collides with every other project in a shared environment that wants a
different Pillow, and it rots once there is no wheel for a new Python.

Reproducibility is a separate problem and wants a separate file. If a release
ever needs byte-identical installs, that is a lock or constraints file applied
at install time, never a permanently narrowed `dependencies`.

#### One file holds the dependencies

`pyproject.toml` is the only place they are written down: runtime packages in
`[project] dependencies`, dev tooling in `[dependency-groups]`. One file, two
tables, nothing to keep in sync by hand. Two files answering one question is
how a runtime list drifts, since nothing can check one against the other.

```bash
pip install -e . --group dev
```

Dev tooling goes in `[dependency-groups]` rather than
`[project.optional-dependencies]`. Extras are published metadata: they land in
the wheel, appear on PyPI, and turn `pip install ls-sql[dev]` into a supported
offer. Dev tooling is a fact about the working copy, not about the installed
artifact. Dependency groups stay local and never ship, which is the honest
description of what `ruff` and `black` are to this project. `--group` needs pip
25.1 or newer, which both the local venv and CI run well past.

The dev pins stay exact while the runtime floors do not, and the asymmetry is
deliberate. A pinned `ruff` freezes a rule set, so local and CI agree on what
counts as a lint failure. `pytest` has no rule set to freeze and stays
unpinned.

### `main()` returns a code, it does not exit

`main()` computes an exit code and returns it. The only `sys.exit()` in the
package is the one wrapping the call, and setuptools already writes that for
the installed `ls-sql` entry point.

The gain is in testing. A returned code is a value a test reads directly, where
`sys.exit()` forces every caller, tests included, to catch a `SystemExit` and
dig the code out of it. Command modules return their codes up to the dispatch,
and `main()` does the same thing one level up. An error inside a command module
is raised instead, and `main()` catches it and reports it, so no command module
writes to stderr.

The cost is a call site that forgets to `return`. An error helper that prints
and returns a code, called without `return` in front of it, turns a failure
into a silent success. Every helper here is named for what it reports rather
than for ending the process.

### Performance targets

- Directory scan 100k files: under 1 second (`os.scandir`)
- Cold start total: under 2 seconds
- Query: linear scan of filenames, no index required at reasonable scale

See [RESULTS.md](RESULTS.md) for the measured numbers over a million files.

### Packaging

```toml
[project]
name = "ls-sql"
requires-python = ">=3.14"
license = "MIT"
license-files = ["LICENSE"]
dependencies = ["mutagen>=1.47.0", "piexif>=1.1.3", "pillow>=12.2.0"]

[project.scripts]
ls-sql = "lssql.cli:main"

[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

`version` is omitted above on purpose. A version number copied into this
document goes stale the moment the next release ships.

The setuptools floor is 77 because of PEP 639. The SPDX `license` string and
`license-files` are rejected by older setuptools, which still expects
`license = {text = "MIT"}`.

The `packages.find` block is what makes the src layout explicit rather than
inferred, so a stray top-level directory can never turn into a shipped package.

## What ls-sql does

- Harvests metadata automatically from JPG, PNG, GIF, WEBP, MP3, M4A, ZIP, CBZ
- Carries a human comment, appended to the filename by hand
- Carries user-defined tags for albums, captions, sequences
- Queries with `SELECT * WHERE`, supporting `=`, `CONTAINS`, `IS NOT NULL`,
  and `IS NULL`
- Keeps no database and no cache

That list is the whole tool. Anything not described in this document or in
[CLI.md](CLI.md) is not implemented, however reasonable it sounds.

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ library? Querying stays fast, but `harvest` and `verify` read every
  byte, so budget real time for those two.
- Multi-user, networked, or cloud storage? Same answer.

Congratulations. Go get proper gear. 🎣

## Out of scope

- Windows. macOS only.
- Cloud sync or remote filesystems.
- Real-time file watching. Use periodic harvest or cron.
- GUI.
- SQLite. Filenames are the database.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and
documentation in this project are written in collaboration with
Artificial Intelligence (AI). The division of labour: the AI explores,
challenges assumptions and edge cases, and drafts; the human
initiates, drafts the designs, explores alongside the AI, reviews
every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

# ls-sql design & specification

## Table of Contents

- L1: [ls-sql design & specification](#ls-sql-design--specification)
  - L3: [Table of Contents](#table-of-contents)
  - L70: [Hatfile](#hatfile)
  - L89: [ls-sql Architecture](#ls-sql-architecture)
  - L106: [Filename specification](#filename-specification)
    - L108: [Hatfile metadata and boundary](#hatfile-metadata-and-boundary)
    - L123: [Tagged key-value format](#tagged-key-value-format)
    - L132: [Character budget](#character-budget)
  - L144: [Tag namespaces](#tag-namespaces)
    - L157: [Namespace rules](#namespace-rules)
    - L167: [Tag reference](#tag-reference)
    - L206: [Note on name hash](#note-on-name-hash)
  - L214: [Album system](#album-system)
    - L221: [Multi select list](#multi-select-list)
  - L227: [Configuration](#configuration)
  - L238: [CLI reference](#cli-reference)
    - L240: [CLI grammar](#cli-grammar)
    - L269: [Query mode](#query-mode)
    - L279: [Harvest mode](#harvest-mode)
    - L289: [Reversal mode](#reversal-mode)
    - L297: [Set mode](#set-mode)
      - L324: [Operators](#operators)
      - L337: [Operator rules](#operator-rules)
      - L349: [Harvest-first](#harvest-first)
      - L354: [`--fh` flag](#--fh-flag)
    - L365: [Flag rules](#flag-rules)
  - L383: [Output style](#output-style)
  - L402: [Implementation](#implementation)
    - L404: [Language](#language)
    - L409: [Key dependencies](#key-dependencies)
    - L421: [Performance targets](#performance-targets)
    - L427: [Packaging](#packaging)
  - L441: [V1 vs V2](#v1-vs-v2)
    - L443: [V1 -- ship it](#v1----ship-it)
    - L451: [V2 -- full fidelity](#v2----full-fidelity)
  - L459: [Edge cases](#edge-cases)
  - L470: [When to stop using ls-sql](#when-to-stop-using-ls-sql)
  - L480: [Out of scope](#out-of-scope)
  - L490: [Granular Details](#granular-details)
    - L492: [`--query` mode](#--query-mode)
    - L511: [`--harvest` mode](#--harvest-mode)
    - L530: [`--remove-all-tags` mode](#--remove-all-tags-mode)
    - L545: [`--verify` mode](#--verify-mode)
    - L561: [EXIF files (`ex:`)](#exif-files-ex)
    - L579: [Audio files (`au:`)](#audio-files-au)
    - L594: [ZIP files (`zi:`)](#zip-files-zi)
      - L621: [Example](#example)
      - L627: [Query examples](#query-examples)
    - L637: [Stable Diffusion (`sd:`) -- v1.x](#stable-diffusion-sd----v1x)
    - L655: [User Defined (`ud:`)](#user-defined-ud)
      - L661: [Album system and `ud:` tags](#album-system-and-ud-tags)
        - L666: [How it works](#how-it-works)
        - L680: [Album example](#album-example)
        - L696: [Album rules](#album-rules)
      - L705: [Repurpose Album tags for multi select list](#repurpose-album-tags-for-multi-select-list)
    - L728: [Duplicate detection](#duplicate-detection)
    - L746: [`--set` mode](#--set-mode)
      - L751: [Tag manipulation logic](#tag-manipulation-logic)
      - L783: [Multi-value separator](#multi-value-separator)
      - L795: [Protected namespaces](#protected-namespaces)
      - L808: [Pipe pattern](#pipe-pattern)
      - L829: [Implementation note](#implementation-note)

---

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

See [HATFILE.md](HATFILE.md)

---

## ls-sql Architecture

Two modes, one tool.

```bash
ls-sql --harvest --target .  # harvest mode -- reads files, renames filenames
ls-sql --target .            # query mode   -- reads filesystem directly, outputs ls-style
```

Harvester touches files. Querier never does. That distinction is absolute.

The filesystem is the only source of truth. There is no database to maintain,
no cache to invalidate, no records to go stale. Everything ls-sql knows lives
in filenames.

---

## Filename specification

### Hatfile metadata and boundary

`^^^` marks the boundary between the original filename and Hatfile metadata.
This is the Hatfile standard. It is not configurable.

```text
{original_filename}^^^{Hatfile_metadata}^^^{human_comment}.{ext}
```

- Left of first `^^^` -- original filename, never modified
- Middle -- tagged key-value pairs
- Right of second `^^^` -- free human comment, optional
- The trailing `^^^` is always present, even without a comment
- Target: under 200 characters total

### Tagged key-value format

All metadata uses `namespace:key=value` pairs separated by `^`. Order does not
matter. Missing fields are skipped cleanly.

```text
ls:hd=20260503^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:dto=2024:07:12
```

### Character budget

```text
A1111 original:       ~19 chars     (e.g. 00234-1234567890.png)
Separator ^^^ x 2:      6 chars
Tagged metadata:      ~80 chars     (reasonable field set)
Human comment:        ~80 chars     remaining budget
Total target:        <200 chars     well within macOS 255 byte limit
```

---

## Tag namespaces

Namespaces keep tags organised and prevent collisions between sources.

```text
au:    audio metadata (MP3, AAC, FLAC, whatever comes next)
ex:    EXIF data
ls:    ls-sql native tags
sd:    Stable Diffusion / A1111 (planned -- v1.x)
ud:    user defined custom tags
zi:    zipfile info (.zip files)
```

### Namespace rules

2-letter namespaces are reserved for ls-sql built-in harvesters. They are short
because they appear in filenames and character budget matters.

- `ud:` is the blessed user namespace for simple custom tags.
- Use 1-letter or 3-letter+ namespaces for your own structured extensions
  (e.g. `myapp:key=value`).
- Use a 2-letter namespace and you are on your own -- harvest will overwrite.

### Tag reference

```text
ls:hd    Harvest date (YYYYMMDD)
ls:fh    File content hash (16 chars SHA256, content fingerprint)
ls:dw   Image width
ls:dh   Image height

ex:dto   Exif DateTimeOriginal
ex:cam   Camera model, slugified (e.g. canon-r5)
ex:fl    Focal length (e.g. 50mm)
ex:ap    Aperture (e.g. f2.8)
ex:iso   ISO value
ex:ss    Shutter speed (e.g. 1-500)
ex:lat   Exif GPSLatitude
ex:lon   Exif GPSLongitude

au:ar    Artist
au:al    Album
au:tt    Track title
au:tn    Track number
au:yr    Year

zi:cnt   total entry count
zi:ext   content types
zi:dot   dot entry count

sd:mn    Model name         -- v1.x
sd:mh    Model hash         -- v1.x
sd:sa    Sampler            -- v1.x
sd:sp    Sampling steps     -- v1.x
sd:sh    Schedule type      -- v1.x
sd:cfg   CFG scale          -- v1.x
sd:sd    Seed               -- v1.x
sd:la    LoRA               -- v1.x

ud:*     Anything that does not overlap with ls-sql native tags
```

### Note on name hash

There is no filename hash tag. You cannot take a hash of a filename that
already contains a hash -- the result would never match anything on rebuild.
The file content hash (`ls:fh`) is the stable fingerprint. That is enough.

---

## Album system

Albums are implemented entirely through user defined tags. No separate data
structure. No database.

[See Granular Details.](#album-system-and-ud-tags)

### Multi select list

[See Granular Details.](#repurpose-album-tags-for-multi-select-list)

---

## Configuration

Configuration is deferred to v1.x. ls-sql v1 uses sensible hardcoded defaults
and requires no configuration file to operate.

- Harvest boundary: `^^^` -- the Hatfile standard, not configurable
- Max filename length: 200 characters
- Fields harvested: all available for the file type

---

## CLI reference

### CLI grammar

Aligned with the mdmap house CLI style in July 2026 (branch
`refactor/mdmap-face-lift`); mdmap is the reference implementation of the
grammar. ls-sql keeps one deliberate divergence: piped mode.

- **All flags, no positionals.** Every mode names the directory or file it
  acts on with `--target PATH`; the positional form was dropped in July 2026.
- **Bare `ls-sql` on a TTY prints help.** The module docstring banner goes to
  stdout, exit 0. Discovering the tool costs nothing and touches nothing.
- **Piped mode is the exception, and it is the product.** When stdin is not a
  TTY, ls-sql enters passthrough parse mode before argparse runs: read paths
  from stdin, parse the Hatfile names, print full paths, exit 0. Flags are
  ignored in piped mode. Unlike the other house CLIs, piped input with no
  flags is not a usage error -- it is the primary Unix-citizen mode.
- **Error style.** Every self-generated error is `ls-sql: <message>` followed
  by the compact USAGE lines, both to stderr, exit 1. Errors never dump the
  full `--help` text.

  ```text
  Usage: ls-sql --target PATH [--query Q | --harvest | --remove-all-tags | --verify | --set TAGS] [options]
         ls <dir> | ls-sql
  ```

- **Exit codes.** `0` success; `1` every ls-sql-generated error, and `--verify`
  when changed content is found (a semantic result, not an error -- the
  message carries no `ls-sql:` prefix); `2` is reserved for argparse's own
  errors (unknown flag, missing value).

### Query mode

```bash
ls-sql --target .                                          # fresh from filesystem
ls-sql -R --target .                                       # recursive
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" --target .    # filtered query
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" --target ~/photos
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" --target .
```

### Harvest mode

```bash
ls-sql --harvest --dry-run --target .                  # preview renames, no changes
ls-sql --harvest --commit --target .                   # execute renames
ls-sql --harvest --commit -R --target .                # recursive harvest
ls-sql --harvest --commit --ext jpg,png --target .     # filter by extension
ls-sql --harvest --commit --max 50 --target .          # limit files per run
```

### Reversal mode

```bash
ls-sql --remove-all-tags --dry-run --target ~/photos   # preview strip
ls-sql --remove-all-tags --commit --target ~/photos    # restore original filenames
ls-sql --remove-all-tags --commit -R --target ~/photos # recursive
```

### Set mode

Write user-defined tags directly into filenames. Harvest-first is automatic.
Dry-run by default. Pass `--commit` to execute.

```bash
# single file
ls-sql --set "ud:album=london-2006" --target photo.jpg
ls-sql --set "ud:album=london-2006" --commit --target photo.jpg

# multiple tags -- caret-separated
ls-sql --set "ud:album=london-2006^ud:where=thames" --commit --target photo.jpg

# directory -- all files in directory
ls-sql --set "ud:trip=london" --commit --target ~/photos/london

# recursive directory
ls-sql --set "ud:trip=london" -R --commit --target ~/photos/london

# select by content hash
ls-sql --fh="ab2c3d,9fs7g1" --set "ud:album=london" --commit --target ~/photos

# pipe from query -- preferred pattern for filtered sets (V2, see Pipe pattern)
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --target ~/photos \
  | ls-sql --set "ud:gear=fuji" --commit
```

#### Operators

```text
ud:key=value    overwrite -- replaces existing value, or creates tag
ud:key=         no-op     -- empty value, skip silently
ud:key+=value   append    -- adds value, semicolon-separated
ud:key+=        no-op     -- empty value, skip silently
ud:key-=value   remove    -- removes value from existing if present
ud:key-=        no-op     -- empty value, skip silently
ud:key==        delete    -- removes the tag entirely
ud:key==value   no-op     -- value present, skip silently
```

#### Operator rules

- Overwrite (`=`) works on any tag, any namespace.
- Append (`+=`) and remove (`-=`) work on any tag. No babysitting.
  Harvest will overwrite machine-generated tags on the next run anyway.
- Multi-value separator is `;` (semicolon). Comma is allowed in values.
- Empty tag after `-=` is removed entirely. Empty tags are noise.
- `ls:fh` is protected. `--set` silently skips it. Content integrity
  is the one thing the tool guards without being asked.
- `--ext` is ignored in `--set` mode. File selection is by path or hash,
  not by extension.

#### Harvest-first

If a file has not been harvested, `--set` harvests it first silently, then
applies the tag. The user does not need to run `--harvest` first.

#### `--fh` flag

Select files by content hash. Comma-separated list of 16-char SHA256 prefixes.
Hash does not change when the filename changes -- stable selector across renames.

```bash
ls-sql --fh="ab2c3d4e5f,9fs7g1h2i3" --set "ud:album=london" --commit --target ~/photos
```

Matches any harvested file whose `ls:fh` value starts with the given prefix.

### Flag rules

- `--target` is required in every non-piped mode. It names the directory or file
  the mode acts on -- there is no positional form.
- `--harvest` without `--dry-run` or `--commit` defaults to `--dry-run`. Safe always.
- `-R` is recursive, same as `ls -R`.
- `--ext` overrules whitelisted extensions -- jpg, jpeg, png, gif, webp, mp3, m4a, zip, cbz.
- `--query` filters output. `FROM` clause is omitted -- there is only one thing to query.
- `--remove-all-tags` strips everything between the first and second `^^^`. The human
  comment right of the second `^^^` is preserved. Fully reversible.
- `--query` output is clean path-per-line with no summary line -- pipeable
  into any Unix tool as-is. There is no `--quiet`; there is nothing to silence.
- `--set` without `--commit` is dry-run. Safe always.
- `--fh` requires `--set`. It is a file selector, not a query.
- `--ext` is ignored when `--set` is active.

---

## Output style

Output prints full path, pipeable, composable result.

```text
/Users/go/SD/outputs/00234^^^sd:mn=sdxl^ls:fh=a3f2c8f91b^^^.png
/Users/go/SD/outputs/00891^^^sd:mn=flux^ls:fh=9b1d4e72ac^^^dog-in-tuxedo.png
```

Pipe it anywhere:

```bash
ls-sql -R --target . | grep "euler-a"
ls-sql --query "SELECT * WHERE sd:mn='flux'" --target . | wc -l
ls-sql --target . | awk '{print $1}' | xargs open
```

---

## Implementation

### Language

Python 3.x. Packaged with `pyproject.toml` for `pip install` and Homebrew
cask distribution.

### Key dependencies

```text
Pillow          image resolution extraction (JPG, PNG, GIF, WEBP)
piexif          EXIF reading for JPG
mutagen         ID3/MP3 metadata extraction
hashlib         SHA256 for file content hash (stdlib)
os.scandir()    fast directory traversal (stdlib)
```

No database dependency. No ORM. No migration files.

### Performance targets

- Directory scan 100k files: under 1 second (`os.scandir`)
- Cold start total: under 2 seconds
- Query: linear scan of filenames, no index required at reasonable scale

### Packaging

```toml
[project]
name = "ls-sql"
version = "1.1.0"
requires-python = ">=3.14"

[project.scripts]
ls-sql = "lssql.cli:main"
```

---

## V1 vs V2

### V1 -- ship it

- Metadata harvested automatically from JPG, PNG, GIF, WEBP, MP3
- Human comment appended manually to filename
- User defined tags for albums, captions, sequences
- Query engine -- `SELECT * WHERE` with `=`, `CONTAINS`, `IS NOT NULL`, `IS NULL`
- No database, no cache

### V2 -- full fidelity

- Prompt summarizer: harvest a short slug from the SD prompt into the filename
- Command line album viewer (Kitty / iTerm2 inline image protocol)
- These are additive. The V1 filename format does not change.

---

## Edge cases

When in doubt, warn and skip. Never guess.

- **`^^^` already in original stem** -- harvester skips and warns.
- **Filename exceeds 200 chars** -- harvester warns before renaming, skips file.
- **File already harvested** -- harvester detects `^^^` and skips. Idempotent.
- **Duplicate files** -- `ls:fh` catches identical content regardless of filename.

---

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ library? You need enterprise tooling and a budget to match.
- Multi-user, networked, or cloud storage? Same answer.

Congratulations. Go get proper gear. 🎣

---

## Out of scope

- Windows. macOS only.
- Cloud sync or remote filesystems.
- Real-time file watching. Use periodic harvest or cron.
- GUI.
- SQLite. Filenames are the database.

---

## Granular Details

### `--query` mode

Scan a directory and filter files using a SQL-like query against harvested tags
in filenames. No database. Reads filenames directly.

```bash
ls-sql --target .
ls-sql -R --target .
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" --target .
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" --target .
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" --target ~/photos
ls-sql --query "SELECT * WHERE ls:fh IS NULL" --target .
```

Supports `=`, `CONTAINS`, `IS NOT NULL`, `IS NULL`. Output is full path per
line, pipeable.

---

### `--harvest` mode

Read file metadata and encode it as tagged key-value pairs into the filename.
Dry-run by default. Pass `--commit` to execute. Idempotent -- already harvested
files are skipped.

```bash
ls-sql --harvest --dry-run --target .
ls-sql --harvest --commit --target .
ls-sql --harvest --commit -R --target ~/photos
ls-sql --harvest --commit --ext jpg,png --target .
ls-sql --harvest --commit --max 50 --target .
```

Supports `--ext` to filter by extension, `--max` to limit files per run,
`-R` for recursive.

---

### `--remove-all-tags` mode

Strip all harvested tags from filenames and restore originals. Human comments
(right of second `^^^`) are preserved. Dry-run by default. Pass `--commit`
to execute.

```bash
ls-sql --remove-all-tags --dry-run --target ~/photos
ls-sql --remove-all-tags --commit --target ~/photos
ls-sql --remove-all-tags --commit -R --target ~/photos
```

Fully reversible. The original filename left of the first `^^^` is never
modified during harvest, so restoration is lossless.

### `--verify` mode

Compare `ls:fh` in filename against current file content hash.

- summary by default, per-file detail with `--verbose`
- exit code non-zero on any mismatch -- scriptable
- read-only, never touches files
- files without `ls:fh` skipped with reason: no ls:fh -- harvest first

```bash
ls-sql --verify --target .
ls-sql --verify -R --target ~/photos
```

---

### EXIF files (`ex:`)

EXIF metadata embedded in JPG files by cameras and photo editors.
Read via `piexif`. No extraction required.

```text
ex:dto   DateTimeOriginal (e.g. 2024:07:12)
ex:cam   Camera model, slugified (e.g. canon-r5)
ex:fl    Focal length (e.g. 50mm)
ex:ap    Aperture (e.g. f2.8)
ex:iso   ISO value
ex:ss    Shutter speed (e.g. 1-500)
ex:lat   GPS latitude
ex:lon   GPS longitude
```

---

### Audio files (`au:`)

ID3 and audio metadata from MP3 files.
Read via `mutagen`. No extraction required.

```text
au:ar    Artist
au:al    Album
au:tt    Track title
au:tn    Track number
au:yr    Year
```

---

### ZIP files (`zi:`)

ZIP and CBZ files are containers. The metadata worth capturing is what's
inside, not the compression. The ZIP format stores its central directory
separately from compressed data, so filenames are readable without
decompression. No extraction required.

macOS resource forks (`__MACOSX/` and `._` sidecar files) are filtered
automatically. They are implementation noise, not real content. Pass
`--include-resource-forks` to include them (planned).

```text
zi:cnt    total entry count (files and directories, including dot entries)
zi:ext    content types, comma-separated extensions, no dots (e.g. jpg,png,txt)
          directories excluded -- extensions only make sense for files
zi:dot    dot entry count (files and directories starting with a dot)
          only present when > 0 -- presence alone is the signal
zi:dir    directory count -- explicit and implicit combined, deduplicated
          explicit: entries whose name ends with /
          implicit: parent path segments inferred from file entries
          NOTE: ZIP directories are optional entries (name ending with /).
          many tools omit them entirely and only write file entries.
          counting implicit dirs ensures zi:dir reflects actual structure.
          a ZIP can also contain thousands of empty explicit directories
          with no file entries at all -- both cases are handled correctly.
```

#### Example

```text
archive^^^ls:hd=20260428^ls:fh=a3f2c8f91b^zi:cnt=42^zi:ext=jpg;png;txt^zi:dot=3^zi:dir=1^^^.zip
```

#### Query examples

```bash
ls-sql --query "SELECT * WHERE zi:dot IS NOT NULL" --target .       # ZIPs with dot entries
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" --target .    # ZIPs with executables
ls-sql --query "SELECT * WHERE zi:cnt IS NOT NULL" --target .       # any harvested ZIP
```

---

### Stable Diffusion (`sd:`) -- v1.x

Generation parameters written into PNG metadata by A1111 and compatible tools.
Read via `Pillow` PNGInfo. Planned for v1.x. Not harvested in v1.

```text
sd:mn    Model name
sd:mh    Model hash
sd:sa    Sampler
sd:sp    Sampling steps
sd:sh    Schedule type
sd:cfg   CFG scale
sd:sd    Seed
sd:la    LoRA
```

---

### User Defined (`ud:`)

Anything that does not overlap with ls-sql native tags.

---

#### Album system and `ud:` tags

Albums are implemented entirely through user defined tags. No separate data
structure. No database.

##### How it works

An album is a `ud:` tag applied consistently across files. The album name
becomes the key. The value is a sequence number.

```text
ud:2006-london=1
ud:2006-london=2
ud:2006-london=3
```

Additional `ud:` tags on the same file carry captions, locations, or any other
per-file metadata.

##### Album example

```text
IMG_4520^^^ex:dto=2006:03:15^ls:fh=9b1d4e72ac^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ex:dto=2006:04:10^ls:fh=c3f8a12b91^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ex:dto=2006:04:15^ls:fh=a3f2c8f91b^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
IMG_4523^^^ex:dto=2006:11:15^ls:fh=d4e9b23c82^ud:2006-london=4^ud:where=oxo-building^^^it-was-like-a-movie.jpg
```

Query an album:

```bash
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" --target ~/photos
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" --target ~/photos | sort
```

##### Album rules

- Album name is the `ud:` key. Sequence value is an integer starting at 1.
- One file can belong to multiple albums -- just add more `ud:` tags.
- Albums have no metadata of their own. The filename is the record.
- Sequence gaps are allowed. Order is explicit and human-controlled.

---

#### Repurpose Album tags for multi select list

`ud:` values can be comma-separated strings. No special syntax. The harvester
treats them as plain text. The meaning is yours.

```text
roast-beef^^^ls:fh=9b1d4e72ac^ud:ingredients=beef;carrot;garlic^^^at-mrs-johnsons.jpg
carbonara^^^ls:fh=a3f2c8f91b^ud:ingredients=garlic;pepper;pork^^^italian-night.jpg
prime-rib^^^ls:fh=c3f8a12b91^ud:ingredients=asparagus;beef;potato^^^my-birthday-dinner.jpg
hamburger^^^ls:fh=d4e9b23c82^ud:ingredients=beef;lettuce;tomato^^^road-trip-2015.jpg
```

Query by ingredient:

```bash
ls-sql --query "SELECT * WHERE ud:ingredients CONTAINS 'beef'" --target ~/recipes
```

Same pattern works for tags, moods, colours, keywords -- anything you'd reach
for a checkbox list. One tag key, comma-separated values, no schema required.

---

### Duplicate detection

`ls:fh` is the stable content fingerprint. Duplicates share the same hash
regardless of filename.

Detect duplicates with a one-liner -- no harvester change needed:

```bash
ls-sql --query "SELECT * WHERE ls:fh IS NOT NULL" -R --target . \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

Prints only files that share a hash with at least one other file.

---

### `--set` mode

`--set` is the write side of ls-sql. It encodes user-defined metadata directly
into filenames using the Hatfile tag format.

#### Tag manipulation logic

Given a harvested filename:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=sunny^^^london.jpg
```

**Overwrite** `--set "ud:tags=rainy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=rainy^^^london.jpg
```

**Append** `--set "ud:tags+=foggy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=rainy;foggy^^^london.jpg
```

**Remove value** `--set "ud:tags-=rainy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=foggy^^^london.jpg
```

**Delete tag** `--set "ud:tags-="`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^^^london.jpg
```

#### Multi-value separator

Semicolon `;` is the multi-value separator. Commas are allowed freely in
values—artist names, album titles, and captions naturally contain commas.
Semicolon is rare enough in metadata to serve as a clean delimiter. Duplicates
are not allowed, and values are always alphabetically sorted.

```text
ud:tags=foggy;london;sunny
au:al=Simon & Garfunkel, Greatest Hits    # comma in value, fine
```

#### Protected namespaces

2-letter namespaces (except `ud:`) are reserved for ls-sql built-in harvesters.
`--set` rejects any operation targeting a reserved namespace and stops with an
error. No files are touched.

```text
ls:fh=abc     error -- ls: is reserved
ex:cam=fuji   error -- ex: is reserved
ud:album=x    allowed -- ud: is the blessed user namespace
myapp:key=x   allowed -- 3-letter+ namespaces are free
```

#### Pipe pattern

The preferred pattern for applying tags to a filtered set of files:

```bash
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --target ~/photos \
  | ls-sql --set "ud:gear=fuji" --commit
```

`--query` output is already clean path-per-line, ready for the pipe. `--set`
reads piped paths from stdin, same as any Unix tool.

**Status: not implemented (V2).** Current piped mode is pure passthrough --
it triggers before argument parsing and ignores all flags, so the downstream
`ls-sql --set ... --commit` above parses-and-prints instead of tagging.
Applying `--set` to piped paths is the intended V2 behaviour of this pattern.

Combining `--query` and `--set` in a single command is not supported.
The pipe is explicit, composable, and shows you what will be tagged before
you commit. That is the Unix way.

#### Implementation note

New module: `setter.py` Mirrors `scanner.py`, `parser.py`, `query.py`. All
plain nouns, no prefix. Tag manipulation logic lives here. `cli.py`
wires in the new mode alongside harvest, remove, verify.

---

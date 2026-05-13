# ls-sql design & specification

## Table of Contents

- [Hatfile](#hatfile)
- [ls-sql Architecture](#ls-sql-architecture)
- [Filename specification](#filename-specification)
- [Tag namespaces](#tag-namespaces)
- [Album system](#album-system)
- [Configuration](#configuration)
- [CLI reference](#cli-reference)
- [Output style](#output-style)
- [Implementation](#implementation)
- [V1 vs V2](#v1-vs-v2)
- [Edge cases](#edge-cases)
- [When to stop using ls-sql](#when-to-stop-using-ls-sql)
- [Out of scope](#out-of-scope)
- [Granular Details](#granular-details)

---

## Hatfile

A Hatfile is a plain filename that carries structured metadata.
No sidecar files. No database. No app required.

The metadata lives between `^^^` boundaries, visible to any file browser,
searchable by Spotlight, greppable from Terminal.

```text
photo^^^ls:hd=20260428^ls:fh=a3f2c8f91b^ex:cam=canon-r5^^^london-2006.jpg
^--- original ---^^--- structured metadata ---^^--- human comment ---^
```

Disposable and rebuildable. The file is the record.

See [HATFILE.md](HATFILE.md)

---

## ls-sql Architecture

Two modes, one tool.

```bash
ls-sql --harvest  # harvest mode -- reads files, renames filenames
ls-sql            # query mode   -- reads filesystem directly, outputs ls-style
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
ex:dto=2024:07:12^ls:fh=a3f2c8f91b^ls:res=512x768
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
sd:    Stable Diffusion / A1111 (planned -- v1.1)
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
ls:fh    File content hash (10 chars SHA256, content fingerprint)
ls:res   Image resolution (WIDTHxHEIGHT)

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

sd:mn    Model name         -- v1.1
sd:mh    Model hash         -- v1.1
sd:sa    Sampler            -- v1.1
sd:sp    Sampling steps     -- v1.1
sd:sh    Schedule type      -- v1.1
sd:cfg   CFG scale          -- v1.1
sd:sd    Seed               -- v1.1
sd:la    LoRA               -- v1.1

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

Configuration is deferred to v1.1. ls-sql v1 uses sensible hardcoded defaults
and requires no configuration file to operate.

- Harvest boundary: `^^^` -- the Hatfile standard, not configurable
- Max filename length: 200 characters
- Fields harvested: all available for the file type

---

## CLI reference

### Query mode

```bash
ls-sql .                                               # fresh from filesystem
ls-sql -R .                                            # recursive
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" .         # filtered query
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" .
```

### Harvest mode

```bash
ls-sql --harvest --dry-run .                           # preview renames, no changes
ls-sql --harvest --commit .                            # execute renames
ls-sql --harvest --commit -R .                         # recursive harvest
ls-sql --harvest --commit --ext jpg,png .              # filter by extension
ls-sql --harvest --commit --max 50 .                   # limit files per run
```

### Reversal mode

```bash
ls-sql --remove-all-tags --dry-run ~/photos            # preview strip
ls-sql --remove-all-tags --commit ~/photos             # restore original filenames
ls-sql --remove-all-tags --commit -R ~/photos          # recursive
```

### Set mode

Write user-defined tags directly into filenames. Harvest-first is automatic.
Dry-run by default. Pass `--commit` to execute.

```bash
# single file
ls-sql --set "ud:album=london-2006" photo.jpg
ls-sql --set "ud:album=london-2006" --commit photo.jpg

# multiple tags -- caret-separated
ls-sql --set "ud:album=london-2006^ud:where=thames" --commit photo.jpg

# directory -- all files in directory
ls-sql --set "ud:trip=london" --commit ~/photos/london

# recursive directory
ls-sql --set "ud:trip=london" -R --commit ~/photos/london

# select by content hash
ls-sql --fh="ab2c3d,9fs7g1" --set "ud:album=london" --commit ~/photos

# pipe from query -- preferred pattern for filtered sets
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --quiet ~/photos \
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

Select files by content hash. Comma-separated list of 10-char SHA256 prefixes.
Hash does not change when the filename changes -- stable selector across renames.

```bash
ls-sql --fh="ab2c3d4e5f,9fs7g1h2i3" --set "ud:album=london" --commit ~/photos
```

Matches any harvested file whose `ls:fh` value starts with the given prefix.

### Flag rules

- `--harvest` without `--dry-run` or `--commit` defaults to `--dry-run`. Safe always.
- `-R` is recursive, same as `ls -R`.
- `--ext` overrules whitelisted extensions -- jpg, jpeg, png, gif, webp, mp3, m4a, zip, cbz.
- `--query` filters output. `FROM` clause is omitted -- there is only one thing to query.
- `--remove-all-tags` strips everything between the first and second `^^^`. The human
  comment right of the second `^^^` is preserved. Fully reversible.
- `--quiet` suppresses the summary line. Output is clean path-per-line,
  pipeable into `--set` or any other Unix tool.
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
ls-sql -R . | grep "euler-a"
ls-sql --query "SELECT * WHERE sd:mn='flux'" . | wc -l
ls-sql . | awk '{print $1}' | xargs open
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
version = "0.14.0"
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
ls-sql .
ls-sql -R .
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" .
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" .
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos
ls-sql --query "SELECT * WHERE ls:fh IS NULL" .
```

Supports `=`, `CONTAINS`, `IS NOT NULL`, `IS NULL`. Output is full path per
line, pipeable.

---

### `--harvest` mode

Read file metadata and encode it as tagged key-value pairs into the filename.
Dry-run by default. Pass `--commit` to execute. Idempotent -- already harvested
files are skipped.

```bash
ls-sql --harvest --dry-run .
ls-sql --harvest --commit .
ls-sql --harvest --commit -R ~/photos
ls-sql --harvest --commit --ext jpg,png .
ls-sql --harvest --commit --max 50 .
```

Supports `--ext` to filter by extension, `--max` to limit files per run,
`-R` for recursive.

---

### `--remove-all-tags` mode

Strip all harvested tags from filenames and restore originals. Human comments
(right of second `^^^`) are preserved. Dry-run by default. Pass `--commit`
to execute.

```bash
ls-sql --remove-all-tags --dry-run ~/photos
ls-sql --remove-all-tags --commit ~/photos
ls-sql --remove-all-tags --commit -R ~/photos
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
ls-sql --verify .
ls-sql --verify -R ~/photos
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
ls-sql --query "SELECT * WHERE zi:dot IS NOT NULL" .      # ZIPs with dot entries
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'exe'" .   # ZIPs with executables
ls-sql --query "SELECT * WHERE zi:cnt IS NOT NULL" .      # any harvested ZIP
```

---

### Stable Diffusion (`sd:`) -- v1.1

Generation parameters written into PNG metadata by A1111 and compatible tools.
Read via `Pillow` PNGInfo. Planned for v1.1. Not harvested in v1.

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
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos | sort
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
ls-sql --query "SELECT * WHERE ud:ingredients CONTAINS 'beef'" ~/recipes
```

Same pattern works for tags, moods, colours, keywords -- anything you'd reach
for a checkbox list. One tag key, comma-separated values, no schema required.

---

### Duplicate detection

`ls:fh` is the stable content fingerprint. Duplicates share the same hash
regardless of filename.

Detect duplicates with a one-liner -- no harvester change needed:

```bash
ls-sql --query "SELECT * WHERE ls:fh IS NOT NULL" -R . \
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
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --quiet ~/photos \
  | ls-sql --set "ud:gear=fuji" --commit
```

`--quiet` strips the summary line from `--query` output, leaving clean
path-per-line for the pipe. `--set` reads piped paths from stdin, same as
any Unix tool.

Combining `--query` and `--set` in a single command is not supported.
The pipe is explicit, composable, and shows you what will be tagged before
you commit. That is the Unix way.

#### Implementation note

New module: `setter.py` Mirrors `scanner.py`, `parser.py`, `query.py`. All
plain nouns, no prefix. Tag manipulation logic lives here. `cli.py`
wires in the new mode alongside harvest, remove, verify.

---

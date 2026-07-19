# ls-sql

> A pipeable extension of `ls` with SQL querying and file metadata harvesting.

## Table of Contents

- L1: [ls-sql](#ls-sql)
  - L5: [Table of Contents](#table-of-contents)
  - L29: [Why](#why)
  - L39: [Design principles](#design-principles)
  - L49: [Example output](#example-output)
  - L60: [Install](#install)
  - L71: [Usage](#usage)
    - L76: [Quick start](#quick-start)
    - L105: [Setting tags manually](#setting-tags-manually)
    - L135: [Pipe mode](#pipe-mode)
  - L150: [Filename convention](#filename-convention)
  - L166: [Tag namespaces](#tag-namespaces)
    - L178: [Tag reference](#tag-reference)
  - L200: [Albums](#albums)
  - L216: [Supported file types](#supported-file-types)
  - L229: [Duplicate detection](#duplicate-detection)
  - L240: [Performance](#performance)
  - L258: [When to stop using ls-sql](#when-to-stop-using-ls-sql)
  - L264: [Target users](#target-users)
  - L271: [Notes](#notes)
  - L280: [Use of AI](#use-of-ai)

## Why

**The filesystem is the source of truth. The filename is the cache.**

Software dies. Filenames don't.

Every file management tool stores metadata in a database separate from the files. The database drifts. Files move. Records go stale. Orphans accumulate. You lose years of organisation because a catalogue got corrupted.

`ls-sql` takes a different approach. Metadata is encoded directly in the filename itself -- visible to any file browser, searchable by Spotlight, greppable from Terminal. No app required. Disposable and rebuildable from filenames alone in seconds.

## Design principles

- The filesystem is the source of truth. Always.
- The filename is the cache. No separate database required.
- Safe by default -- dry-run unless `--commit` is explicit.
- Unix citizen -- pipeable, composable, stays out of the way.
- File hash -- stable content fingerprint that survives renames.
- Fully reversible -- `--remove-all-tags` restores original filenames exactly.
- Target platform is macOS. 255 character filename limit applies.

## Example output

```text
/Users/go/SD/outputs/00234^^^sd:mn=sdxl^ls:fh=a3f2c8f91b^^^.png
/Users/go/SD/outputs/00891^^^sd:mn=flux^ls:fh=9b1d4e72ac^^^dog-in-tuxedo.png
```

Full path per line -- pipeable, greppable, composable. The metadata rides
inside the filename between `^^^` boundaries; no database ever enters the
picture.

## Install

Requires Python 3.14 or newer. Target platform is macOS.

```bash
pipx install "git+https://github.com/east-van-ai/ls-sql.git@stable"
```

`@stable` tracks the promoted release branch (see [RELEASING.md](RELEASING.md)).
For development, clone the repo and `pip install -e .` in a venv.

## Usage

Run bare `ls-sql` to print the built-in help. All modes name their target
with `--target` -- there is no positional argument.

### Quick start

```bash
# Harvest metadata into filenames (preview first)
ls-sql --harvest --dry-run --target ~/SD/outputs

# Commit the harvest
ls-sql --harvest --commit --target ~/SD/outputs

# Query the filesystem
ls-sql --target ~/SD/outputs

# SQL query
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --target ~/photos

# Tag presence
ls-sql --query "SELECT * WHERE ex:cam IS NOT NULL" --target ~/photos

# Substring match on ZIP contents
ls-sql --query "SELECT * WHERE zi:ext CONTAINS 'jpeg'" --target ~/zips

# Recursive
ls-sql -R --target ~/SD/outputs

# Remove all ls-sql tags, restore original filenames
ls-sql --remove-all-tags --dry-run --target ~/photos
ls-sql --remove-all-tags --commit --target ~/photos
```

### Setting tags manually

`--set` writes user-defined tags directly into filenames. If a file has not been harvested yet, `--set` harvests it first, then applies the tag.

```bash
# Set a tag on a single file (dry-run by default)
ls-sql --set "ud:album=london-2006" --target photo.jpg

# Commit
ls-sql --set "ud:album=london-2006" --commit --target photo.jpg

# Set multiple tags (caret-separated)
ls-sql --set "ud:album=london-2006^ud:where=thames" --commit --target photo.jpg

# Append to an existing value
ls-sql --set "ud:weather+=rainy" --commit --target photo.jpg

# Remove a specific value
ls-sql --set "ud:weather-=rainy" --commit --target photo.jpg

# Remove a tag entirely
ls-sql --set "ud:weather==" --commit --target photo.jpg

# Apply to a whole directory
ls-sql --set "ud:trip=london-2006" --commit --target ~/photos/london

# Select by content hash -- hash does not change when filename changes
ls-sql --fh="ab2c3d;9fs7g1" --set "ud:album=london-2006" --commit --target ~/photos
```

### Pipe mode

`ls-sql` reads from stdin automatically when piped. Output is full path per line, composable with standard Unix tools.

```bash
# Count matches
ls-sql --query "SELECT * WHERE sd:mn='flux'" --target . | wc -l

# Open results
ls-sql --target . | awk '{print $1}' | xargs open

# Grep output directly
ls-sql -R --target . | grep "euler-a"
```

## Filename convention

`ls-sql` implements the **Hatfile** convention -- a filename-embedded metadata standard using `^^^` as a harvest boundary.

```text
IMG-1234567890-1234567890^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:dto=2024:07:12^^^mom-at-wedding-1994-06-24.png
^-- original, untouched --^^^--- structured metadata, tagged key-value pairs --------------------------^^^--- human comment ------^
```

- Left of first `^^^` -- original filename, never modified
- Middle -- tagged key-value pairs
- Right of second `^^^` -- free human comment, optional
- Target: under 200 characters total

See [HATFILE.md](HATFILE.md) for the full convention.

## Tag namespaces

```text
ls:    ls-sql native tags          (2-letter, reserved)
ex:    EXIF metadata               (2-letter, reserved)
au:    Audio metadata              (2-letter, reserved)
zi:    ZIP / CBZ metadata          (2-letter, reserved)
ud:    User defined custom tags    (blessed user namespace)
```

2-letter namespaces are reserved for ls-sql built-in harvesters. Use `ud:` for custom tags. Use 1-letter or 3-letter+ namespaces for your own extensions (e.g. `myapp:key=value`).

### Tag reference

```text
ls:hd    Harvest date (YYYYMMDD)
ls:fh    File content hash (16 chars SHA-256)
ls:dw    Image width
ls:dh    Image height

ex:dto   EXIF DateTimeOriginal
ex:cam   Camera model, slugified
ex:ap    Aperture (e.g. f2.8)

au:ar    Artist
au:al    Album
au:tt    Track title

zi:cnt   ZIP entry count
zi:ext   ZIP content types (semicolon-separated)

ud:*     Anything. Example: ud:album=london-2006
```

## Albums

Albums are implemented entirely through `ud:` tags. No database. No schema.

```text
IMG_4520^^^ls:hd=20260503^ls:fh=9b1d4e72ac6a0mha^ex:dto=2006:03:15^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ls:hd=20260503^ls:fh=c3f8a12b916531uj^ex:dto=2006:04:10^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^ex:dto=2006:04:15^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
```

Query an album:

```bash
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" --target ~/photos
```

## Supported file types

```text
JPG    EXIF data -- camera, date, aperture
PNG    Image dimensions
GIF    Image dimensions
WEBP   Image dimensions
MP3    ID3 tags -- artist, album, title
M4A    iTunes atoms -- artist, album, title
ZIP    Entry count, content types
CBZ    Comic Book ZIP, same as ZIP
```

## Duplicate detection

`ls:fh` is the stable content fingerprint. Use it to find duplicates:

```bash
ls-sql --query "SELECT * WHERE ls:fh IS NOT NULL" -R --target . \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

## Performance

ls-sql reads filenames directly. File size is irrelevant.

```text
 Casual photographer:   5,000 - 20,000 files   totally normal
Serious photographer:  20,000 - 50,000 files   power user
       SD enthusiast:  10,000 - 30,000 files   reasonable
   Obsessive SD user:  50,000+ files           okay buddy
 100,000 files @ 1MB:       ~100GB             you are an enterprise user
```

```text
    External HDD:   ~20,000 files per second
External USB SSD:   ~50,000 files per second
    Internal SSD:  ~100,000 files per second
```

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ library? You need enterprise tooling and a budget to match.
- Need multi-user, networked, or cloud storage? Same answer.

## Target users

- Stable Diffusion / A1111 image generators
- Photographers with EXIF-rich libraries
- Small web servers with image collections
- Anyone who lives in Terminal

## Notes

- Errors print as `ls-sql: <message>` with a compact usage line; exit codes
  are 0 (success), 1 (ls-sql errors, and `--verify` when content changed),
  2 (argument-parsing errors).
- [DESIGN.md](DESIGN.md) is the full internal spec -- CLI grammar, edge
  cases, V1/V2 scope. [HATFILE.md](HATFILE.md) documents the filename
  convention standalone.

## Use of AI

This project is built with Artificial Intelligence (AI), deliberately
and in the open. Code and documentation are written in collaboration
with remote and local AI; design decisions, code review, and final
judgment stay human.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

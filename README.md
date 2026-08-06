# ls-sql

> A pipeable extension of `ls` with SQL querying and file metadata harvesting.

## Table of Contents

- [ls-sql](#ls-sql)
  - [Table of Contents](#table-of-contents)
  - [Why](#why)
  - [Design principles](#design-principles)
  - [Example output](#example-output)
  - [Install](#install)
  - [Usage](#usage)
    - [Quick start](#quick-start)
    - [Setting tags manually](#setting-tags-manually)
    - [Pipe mode](#pipe-mode)
  - [Filename convention](#filename-convention)
  - [Tag namespaces](#tag-namespaces)
    - [Tag reference](#tag-reference)
  - [Albums](#albums)
  - [Supported file types](#supported-file-types)
  - [Duplicate detection](#duplicate-detection)
  - [Performance](#performance)
  - [When to stop using ls-sql](#when-to-stop-using-ls-sql)
  - [Target users](#target-users)
  - [Notes](#notes)
  - [Use of AI](#use-of-ai)

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
- Fully reversible -- `ls-sql reset` restores original filenames exactly.
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

A command, then a path, then options.

```text
ls-sql <command> PATH [options]
```

There are five commands: `list`, `harvest`, `set`, `verify`, and `reset`. The
command goes right after `ls-sql` and the path right after the command. Run
bare `ls-sql` for the built-in help, or a bare command word (`ls-sql harvest`)
for that command's help.

### Quick start

```bash
# Harvest metadata into filenames (preview first -- dry run is the default)
ls-sql harvest ~/SD/outputs

# Commit the harvest
ls-sql harvest ~/SD/outputs --commit

# List the filesystem
ls-sql list ~/SD/outputs

# SQL query
ls-sql list ~/photos --query "SELECT * WHERE ex:cam='fujifilm-x-t5'"

# Tag presence
ls-sql list ~/photos --query "SELECT * WHERE ex:cam IS NOT NULL"

# Substring match on ZIP contents
ls-sql list ~/zips --query "SELECT * WHERE zi:ext CONTAINS 'jpeg'"

# Recursive
ls-sql list ~/SD/outputs -R

# Check that content still matches the hash in the filename
ls-sql verify ~/SD/outputs

# Remove all ls-sql tags, restore original filenames
ls-sql reset ~/photos
ls-sql reset ~/photos --commit
```

### Setting tags manually

`set` writes user-defined tags directly into filenames. The tags ride `--tags`.
If a file has not been harvested yet, `set` harvests it first, then applies the
tag.

```bash
# Set a tag on a single file (dry-run by default)
ls-sql set photo.jpg --tags "ud:album=london-2006"

# Commit
ls-sql set photo.jpg --tags "ud:album=london-2006" --commit

# Set multiple tags (caret-separated)
ls-sql set photo.jpg --tags "ud:album=london-2006^ud:where=thames" --commit

# Append to an existing value
ls-sql set photo.jpg --tags "ud:weather+=rainy" --commit

# Remove a specific value
ls-sql set photo.jpg --tags "ud:weather-=rainy" --commit

# Remove a tag entirely
ls-sql set photo.jpg --tags "ud:weather==" --commit

# Apply to a whole directory
ls-sql set ~/photos/london --tags "ud:trip=london-2006" --commit

# Select by content hash -- hash does not change when filename changes
ls-sql set ~/photos --tags "ud:album=london-2006" --fh "ab2c3d;9fs7g1" --commit
```

### Pipe mode

`list` prints one full path per line with no summary, so it composes with
standard Unix tools.

```bash
# Count matches
ls-sql list . --query "SELECT * WHERE sd:mn='flux'" | wc -l

# Open results
ls-sql list . | awk '{print $1}' | xargs open

# Grep output directly
ls-sql list . -R | grep "euler-a"
```

A bare `ls-sql` reads paths from stdin, parses the Hatfile names, and prints
them back. That is the passthrough mode, and it is the only case where stdin
is read.

```bash
ls ~/photos | ls-sql
```

With a command word present, stdin is left alone. `ls . | ls-sql harvest .`
ignores the pipe rather than erroring, because an inherited pipe (from a shell
pipeline, a Makefile, or any subprocess) is indistinguishable from a
deliberate one.

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
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
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
ls-sql list . -R --query "SELECT * WHERE ls:fh IS NOT NULL" \
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
  are 0 (success), 1 (ls-sql errors, and `verify` when content changed),
  2 (argument-parsing errors, including an unknown command).
- Options are scoped to their command. `--commit` on `list` is an error, not
  something quietly ignored.
- [DESIGN.md](DESIGN.md) is the full internal spec -- CLI grammar, output
  style, edge cases. [HATFILE.md](HATFILE.md) documents the filename
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

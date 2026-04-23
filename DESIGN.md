# ls-sql design & specification

## Architecture

Two modes, one tool.

```bash
ls-sql --harvest  # harvest mode - reads files, renames filenames
ls-sql            # query mode   - reads filesystem directly, outputs ls-style
```

Harvester touches files. Querier never does.

The filesystem is the only source of truth. There is no database to maintain, no cache to invalidate, no records to go stale. Everything ls-sql knows lives in filenames.

---

## Filename specification

### Harvest boundary

`^^^` marks the boundary between the original filename and harvested metadata. User-configurable in `ls-sql.yaml`.

```text
{original_filename}^^^{tagged_metadata}^^^{human_comment}.{ext}
```

- Left of first `^^^` -- original filename, never modified
- Middle -- tagged key-value pairs
- Right of second `^^^` -- free human comment, optional
- Target: under 200 characters total

### Tagged key-value format

All metadata uses `namespace:key=value` pairs separated by `^`. Order does not matter. Missing fields are skipped cleanly.

```text
sd:mn=sdxl^sd:cfg=7.5^ex:dto=2024:07:12^ls:fh=a3f2c8f91b^ls:res=512x768
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
ls:    ls-sql native tags
sd:    Stable Diffusion / A1111
ex:    EXIF data
au:    audio metadata (MP3, AAC, FLAC, whatever comes next)
ud:    User defined custom tags
```

### Tag reference

```text
ls:hd    Harvest date (YYYYMMDD)
ls:fh    File content hash (10 chars SHA256, content fingerprint)
ls:res   Image resolution (WidthxHeight)

sd:mn    Model name
sd:mh    Model hash
sd:sa    Sampler
sd:sp    Sampling steps
sd:sh    Schedule type
sd:cfg   CFG scale
sd:sd    Seed
sd:la    Lora

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

ud:*     Anything that does not overlap with ls-sql native tags
```

### Note on name hash

There is no filename hash tag. You cannot take a hash of a filename that already contains a hash. The result would never match anything on rebuild. The file content hash (`ls:fh`) is the stable fingerprint. That is enough.

---

## Album system

Albums are implemented entirely through user defined tags. No separate data structure. No database.

### How it works

An album is a `ud:` tag namespace applied consistently across files. The album name becomes the key. The value is a sequence number.

```text
ud:2006-london=1
ud:2006-london=2
ud:2006-london=3
```

Additional `ud:` tags on the same file carry captions, locations, or any other per-file metadata.

### Album example

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

### Album rules

- Album name is the `ud:` key. Sequence value is an integer starting at 1.
- One file can belong to multiple albums -- just add more `ud:` tags.
- Albums have no metadata of their own. The filename is the record.
- Sequence gaps are allowed. Order is explicit and human-controlled.

## Repurpose Album tags for multi select list

### Multi-value tags

`ud:` values can be comma-separated strings. No special syntax. The harvester treats them as plain text. The meaning is yours.

```text
roast-beef^^^ls:fh=9b1d4e72ac^ud:ingredients=beef,garlic,carrot^^^at-mrs-johnsons.jpg
carbonara^^^ls:fh=a3f2c8f91b^ud:ingredients=pork,garlic,pepper^^^italian-night.jpg
prime-rib^^^ls:fh=c3f8a12b91^ud:ingredients=beef,potato,asparagus^^^my-birthday-dinner.jpg
hamburger^^^ls:fh=d4e9b23c82^ud:ingredients=beef,tomato,lettuce^^^road-trip-2015.jpg
```

Query by ingredient:

```bash
ls-sql --query "SELECT * WHERE ud:ingredients CONTAINS 'beef'" ~/recipes
```

Same pattern works for tags, moods, colours, keywords -- anything you'd reach for a checkbox list. One tag key, comma-separated values, no schema required.

---

## Configuration

`ls-sql.yaml` lives in the target directory or `~/.config/ls-sql/ls-sql.yaml`.

```yaml
separator: "^^^"

fields:
  ls:
    - fh
    - res
    - hd

  sd:
    - mn
    - cfg
    - sa

  exif:
    - cam
    - iso
    - ss

max_filename_chars: 200
```

User picks which fields to harvest. Order in config determines order in filename.

---

## CLI reference

```bash
# Query modes
ls-sql .                                              # fresh from filesystem
ls-sql -R .                                           # recursive
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" .        # filtered query
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos
ls-sql --query "SELECT filename, directory" .         # select filename and directory
ls-sql --query "SELECT pwd-directory-filename" .      # absolute path of the file and its name combined

# Harvest modes
ls-sql --harvest --dry-run .                          # preview renames, no changes
ls-sql --harvest --commit .                           # execute renames
ls-sql --harvest --commit -R .                        # recursive harvest

# Reversal
ls-sql --remove-all-tags --dry-run ~/photos           # preview strip
ls-sql --remove-all-tags --commit ~/photos            # restore original filenames
```

### Flag rules

- `--harvest` without `--dry-run` or `--commit` defaults to `--dry-run`. Safe always.
- `-R` is recursive, same as `ls -R`.
- `--query` filters output. `FROM` clause is omitted -- there is only one thing to query.
- `--remove-all-tags` strips everything between the right of first `^^^` and the second. Fully reversible. This does not remove the right of the second closing `^^^`.

---

## Output style

Output prints full path, pipeable, composable result.

```text
/Users/go/SD/outputs/00234^^^sd:mn=sdxl^ls:fh=a3f2c8f91b.png
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

Python 3.x. Packaged with `pyproject.toml` for `pip install` and Homebrew cask distribution.

### Key dependencies

```text
Pillow          PNG metadata extraction (A1111 PNGInfo)
piexif          EXIF reading for JPG
mutagen         ID3/MP3 metadata extraction
pyyaml          Config file parsing
hashlib         SHA256 for file content hash
os.scandir()    Fast directory traversal
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
version = "0.6.1"
requires-python = ">=3.14"

[project.scripts]
ls-sql = "lssql.cli:main"
```

---

## V1 vs V2

### V1 -- ship it

- Hard metadata harvested automatically from PNG / EXIF
- Human comment appended manually to filename
- User defined tags for albums, captions, sequences
- No database, no cache, no dependencies beyond Python

### V2 -- full fidelity

- Prompt summarizer: harvest a short slug from the SD prompt into the filename
- Command line album viewer (Kitty / iTerm2 inline image protocol)
- These are additive. The V1 filename format does not change.

---

## Edge cases

When there is doubt, warn and skip/halt the operation.

- **`^^^` already in filename** -- harvester skips and warns. User resolves via config.
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

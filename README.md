# ls-sql

> A pipeable extension of `ls` with SQL querying and file metadata harvesting.

## The idea in one sentence

**The filesystem is the source of truth. The filename is the cache.**

## Why

Software dies. Filenames don't.

Every file management tool stores metadata in a database separate from the files. The database drifts. Files move. Records go stale. Orphans accumulate. You lose years of organisation because a catalog got corrupted.

`ls-sql` takes a different approach. Metadata is encoded and lives in the filename itself, visible to any file browser, searchable by Spotlight, greppable from Terminal -- no app required. It is disposable and rebuildable from filenames alone in seconds.

## Design principles

- The filesystem is the source of truth. Always.
- The filename is the cache. No separate database required.
- Safe by default -- dry-run unless `--commit` is explicit.
- Unix citizen -- pipeable, composable, stays out of the way.
- File hash -- fast lookup without losing filename flexibility.
- Fully reversible -- `--remove-all-tags` puts everything back.
- Target platform is macOS. 255 character filename limit applies.

## Quick start

```bash
# Harvest metadata into filenames (preview first)
ls-sql --harvest --dry-run ~/SD/outputs

# Commit the harvest
ls-sql --harvest --commit ~/SD/outputs

# Query fresh from filesystem
ls-sql ~/SD/outputs

# SQL query (FROM clause omitted -- there is only one thing to query)
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" ~/photos

# Recursive
ls-sql -R ~/SD/outputs

# Remove all ls-sql tags, restore original filenames
ls-sql --remove-all-tags --dry-run ~/photos
ls-sql --remove-all-tags --commit ~/photos
```

## Setting tags manually

`--set` writes user-defined tags directly into filenames. Harvest-first is
automatic -- if a file has not been harvested yet, `--set` harvests it first,
then applies the tag.

```bash
# Set a tag on a single file (dry-run by default)
ls-sql --set "ud:album=london-2006" photo.jpg

# Commit
ls-sql --set "ud:album=london-2006" --commit photo.jpg

# Set multiple tags (caret-separated)
ls-sql --set "ud:album=london-2006^ud:where=thames" --commit photo.jpg

# Append to an existing value
ls-sql --set "ud:tags+=rainy" --commit photo.jpg

# Remove a specific value
ls-sql --set "ud:tags-=rainy" --commit photo.jpg

# Remove a tag entirely
ls-sql --set "ud:tags-=" --commit photo.jpg

# Apply to a whole directory
ls-sql --set "ud:trip=london-2006" --commit ~/photos/london

# Apply to files matching a query -- pipe pattern
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --quiet ~/photos \
  | ls-sql --set "ud:gear=fuji" --commit

# Select by content hash -- hash does not change when filename changes
ls-sql --fh="ab2c3d,9fs7g1" --set "ud:album=london-2006" --commit
```

## Filename convention

`ls-sql` implements the **Hatfile** convention -- a filename-embedded metadata
standard using `^^^` as a harvest boundary.

```text
00234-1234567890^^^sd:mn=sdxl^sd:sampler=euler-a^ex:dto=2024:07:12^ls:fh=a3f2c8f91b^ls:res=512x768^ls:hd=20260415^^^mom-at-wedding-1994-06-24.png
^--- original, untouched ---^^--- structured metadata, tagged key-value pairs ------------------------^^--- human comment ----------------------^
```

- Left of first `^^^` -- original filename, never modified
- Middle -- tagged key-value pairs
- Right of second `^^^` -- free human comment, optional
- Target: under 200 characters total

## Tag namespaces

Namespaces keep tags organised and avoid collisions between sources.

```text
ls:    ls-sql native tags          (2-letter, reserved)
ex:    EXIF namespace              (2-letter, reserved)
au:    Audio metadata              (2-letter, reserved)
zi:    ZIP/CBZ metadata            (2-letter, reserved)
sd:    Stable Diffusion            (2-letter, reserved, v1.1)
ud:    User defined custom tags    (blessed user namespace)
```

2-letter namespaces are reserved for ls-sql built-in harvesters. Use `ud:` for
custom tags. Use 1-letter or 3-letter+ namespaces for your own structured
extensions (e.g. `myapp:key=value`).

### Tag reference

```text
ls:hd    Harvest date
ls:fh    File content hash (10 chars SHA256, content fingerprint)
ls:res   Image resolution

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

### User defined tags and albums

Albums are implemented entirely through `ud:` tags. No database. No schema.

```text
IMG_4520^^^ex:dto=2006:03:15^ls:fh=9b1d4e72ac^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ex:dto=2006:04:10^ls:fh=c3f8a12b91^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ex:dto=2006:04:15^ls:fh=a3f2c8f91b^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
```

Query an album:

```bash
ls-sql --query "SELECT * WHERE ud:2006-london IS NOT NULL" ~/photos
```

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

Use `--quiet` to suppress the summary line and get clean path-per-line output
for piping:

```bash
ls-sql --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" --quiet ~/photos \
  | ls-sql --set "ud:gear=fuji" --commit
```

## Supported file types

- PNG  -- Portable - Stable Diffusion / A1111 generated images
- JPG  -- Photographer EXIF data
- GIF  -- Traditional - Graphics Interchange Format
- WEBP -- Modern - Lossless or Lossy
- MP3  -- Music ID3 tags
- M4A  -- MP4 iTunes atoms
- ZIP  -- file count, content types, dot entries, directory structure
- CBZ  -- Comic Book ZIP, same as ZIP
- PDF  -- planned

## Duplicate detection

`ls:fh` is the stable content fingerprint. Use it to find duplicates:

```bash
ls-sql --query "SELECT * WHERE ls:fh IS NOT NULL" -R . \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

## Installation

```bash
brew install --cask ls-sql
```

## Performance

ls-sql reads filenames directly. File size is irrelevant.

### Scale reference

```text
 Casual photographer:   5,000 - 20,000 files   totally normal
Serious photographer:  20,000 - 50,000 files   power user
       SD enthusiast:  10,000 - 30,000 files   reasonable
   Obsessive SD user:  50,000+ files           okay buddy 😄
 100,000 files @ 1MB:       ~100GB             you are an enterprise user
```

### Speed reference

```text
    External HDD:   ~20,000 files per second
External USB SSD:   ~50,000 files per second
    Internal SSD:  ~100,000 files per second
```

If your library exceeds these comfortable limits, consider faster storage.
ls-sql is not the bottleneck -- your drive is.

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ image library? You need enterprise tooling and a budget to match.
- Need multi-user, networked, or cloud storage? Same answer.

Congratulations. Go get proper gear. 🎣

## Target users

- Stable Diffusion / A1111 image generators
- Photographers with EXIF-rich libraries
- Small web servers with image collections
- Anyone who lives in Terminal

## What's next? 🔮

- Command line album viewer for Kitty, iTerm2, or Terminal
- Harvester with AI prompt summarizer

## Status

Final development phase. See [DESIGN.md](DESIGN.md) for full specification.

## License

MIT

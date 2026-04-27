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
# sd:mn means Stable Diffusion Model Name
ls-sql --query "SELECT * WHERE sd:mn='sdxl'" ~/SD/outputs

# Recursive
ls-sql -R ~/SD/outputs

# Remove all ls-sql tags, restore original filenames
ls-sql --remove-all-tags --dry-run ~/photos
ls-sql --remove-all-tags --commit ~/photos
```

## Filename convention

`ls-sql` implements the **Hatfile** convention -- a filename-embedded metadata
standard using `^^^` as a harvest boundary.

```text
00234-1234567890^^^sd:mn=sdxl^sd:sampler=euler-a^ex:dto=2024:07:12^ls:fh=a3f2c8f91b^ls:res=512x768^ls:hd=20260415^^^mom-at-wedding-1994-06-24.png
^--- original, untouched ---^^--- structured metadata, tagged key-value pairs ------------------------^^--- human comment ----------------------^
```

- Left of first `^^^` -- original filename, never modified
- Middle -- tagged key-value pairs, defined in config
- Right of second `^^^` -- free human comment, optional
- Target: under 200 characters total
- `^^^` separator is user-defined in config

## Tag namespaces

Namespaces keep tags organised and avoid collisions between sources.

```text
ls:    ls-sql native tags
sd:    Stable Diffusion namespace
ex:    EXIF namespace
ud:    User defined custom tags
```

### Tag reference

```text
ls:hd    Harvest date
ls:fh    File content hash (10 chars SHA256, content fingerprint)
ls:res   Image resolution

sd:mn    Stable Diffusion model name
sd:cfg   CFG scale
sd:sd    Seed

ex:dto   EXIF DateTimeOriginal
ex:lat   EXIF GPSLatitude
ex:ap    Aperture (e.g. f2.8)

ud:*     Anything that does not overlap with ls-sql native tags
         Example: ud:colours=red
```

### User Defined Tags and Album

Using `ud:london-2006` as a custom album

```text
IMG_4520^^^ex:dto=2006:13:15^ls:fh=9b1d4e72ac^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ex:dto=2006:14:10^ls:fh=c3f8a12b91^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ex:dto=2006:14:15^ls:fh=a3f2c8f91b^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
IMG_4523^^^ex:dto=2006:23:15^ls:fh=d4e9b23c82^ud:2006-london=4^ud:where=oxo-building^^^it-was-like-a-movie.jpg
```

## Output style

Output prints full path, pipeable, composable result.

```text
/Users/go/SD/outputs/00234^^^sd:mn=sdxl^ls:fh=a3f2c8f91b.png
/Users/go/SD/outputs/00891^^^sd:mn=flux^ls:fh=9b1d4e72ac^^^dog-in-tuxedo.png
```

Pipe it anywhere:

```bash
ls-sql -R . | grep "euler-a"
ls-sql --query "SELECT * WHERE sd:mn='flux'" | wc -l
ls-sql . | awk '{print $1}' | xargs open
```

## Supported file types

- PNG  -- Portable - Stable Diffusion / A1111 generated images
- JPG  -- Photographer EXIF data
- MP3  -- Music ID3 tags
- GIF  -- Traditional - Graphics Interchange Format
- WEBP -- Modern - Lossless or Lossy
- PDF  -- planned

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

If your library exceeds these comfortable limits, consider faster storage. ls-sql is not the bottleneck -- your drive is.

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

## What's next? What are in our backlog? 🔮

- Command Line Album viewer for Kitty, iTerm2, or Terminal
- Harvester with AI prompt summarizer

## Status

Early development phase. See [DESIGN.md](DESIGN.md) for full specification.

## License

MIT

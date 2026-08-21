# Hatfile Convention

> A filename-embedded metadata standard. No database required.

## The idea

Metadata belongs with the file, not in a separate database.

Every file management tool stores metadata elsewhere. The database drifts. Files move. Records go stale. Apps get abandoned. You lose years of organisation because a catalogue got corrupted.

Hatfile takes a different approach. Metadata lives in the filename itself, visible to any file browser, searchable by Spotlight, greppable from Terminal. No app required. No database to maintain. No records to go stale.

## The boundary

`^^^` marks the harvest boundary. Three carets. Visually distinct. Rare enough in natural filenames to avoid collisions.

```text
{original}^^^{tagged_metadata}^^^{human_comment}.{ext}
```

- Left of the first `^^^` sits the original filename, never modified.
- Between the boundaries sits the structured key-value metadata.
- Right of the second `^^^` sits a free human comment, and it is optional.
- The trailing `^^^` is always present, even without a comment.

### Example

```text
IMG_4521^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^ex:dto=2006:04:10^ud:2006-london=2^^^is-it-raining.jpg
```

## Tag format

Tags use `namespace:local-key=value` pairs separated by `^`.

```text
ls:hd=20260503^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:dto=2024:07:12
```

Order does not matter. Missing fields are skipped cleanly.

## Namespaces

```text
ls:    Hatfile native tags
ex:    EXIF metadata
au:    Audio metadata (MP3, M4A)
zi:    ZIP / CBZ metadata
ud:    User defined custom tags
```

2-letter namespaces are reserved for ls-sql built-in harvesters. Use `ud:` for custom tags. Use 1-letter or 3-letter+ namespaces for your own extensions (e.g. `myapp:key=value`).

## Tag reference

```text
ls:hd    Harvest date (YYYYMMDD)
ls:fh    File content hash (16 chars SHA-256)
ls:dw    Image width
ls:dh    Image height

ex:dto   EXIF DateTimeOriginal
ex:cam   Camera model, slugified
ex:iso   ISO value
ex:ap    Aperture (e.g. f2.8)
ex:fl    Focal length (e.g. 50mm)

au:ar    Artist
au:al    Album
au:tt    Track title
au:tn    Track number
au:yr    Year

zi:cnt   ZIP entry count
zi:ext   ZIP content types (semicolon-separated)

ud:*     Anything that does not overlap with native tags
```

## Rules

- `^^^` is the standard boundary. It is not configurable.
- Left of the first `^^^` is never modified by any Hatfile-compliant tool.
- Tags are always lowercase `namespace:local-key=value`.
- The trailing `^^^` is always appended, comment or not.
- Filenames must stay under 200 characters total.
- Filenames with `^^^` already in the original stem are not supported.
- Original filename stem must be 80 characters or fewer.

## Reversibility

Stripping all tags between the first and second `^^^` restores the original filename exactly. Hatfile operations are fully reversible by design.

## Use cases

- Photographer EXIF-rich JPG collections
- Music libraries with ID3 tags
- ZIP and CBZ comic archives
- Stable Diffusion / A1111 image libraries
- Any large file collection that lives on a filesystem

## Reference implementation

`ls-sql` is a pipeable CLI tool for harvesting and querying Hatfile metadata.

```bash
ls-sql harvest ~/photos
ls-sql list ~/photos --query "SELECT * WHERE ex:cam='fujifilm-x-t5'"
```

More at [github.com/east-van-ai](https://github.com/east-van-ai)

## Status

Early standard. Stable filename format. Reference implementation active.

Contact: <east-van-ai@proton.me>

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

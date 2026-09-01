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

## Any tool can read it

The tags sit in the name, so a program that has never heard of Hatfile can still answer a question about them. No index, no plugin, no format support. Measured against 1,048,576 generated files on an internal SSD, all three of these return the same 65,536 matches:

| | | |
| --- | --- | --- |
| `rg --files -g "*evai:fruit=apple*"` | 1.0 sec | ripgrep, walks in parallel |
| `ls-sql list --query "SELECT * WHERE evai:fruit='apple'"` | 13.8 sec | Python, parses each name into tags |
| `find -name "*evai:fruit=apple*"` | 17.6 sec | one thread, stats each entry |

None of them knows what a Hatfile is. `find` is already on every Unix machine and needs nothing installed. ripgrep has to be installed, and repays it by answering thirteen times faster than the reference implementation. That spread is the point: the interface is a glob against a filename, so the convention outlives any single tool that reads it, this one included.

Which tool leads depends on the disk. Repeat the same query against an external hard drive and ripgrep's advantage disappears: 5m26s against ls-sql's 6m08s, close enough that the two swap places between runs. Many threads keep a solid-state queue full, and a single head cannot be kept full at all. No reader is the right reader everywhere, and a convention only one of them could read would have to pick.

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

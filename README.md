# ls-sql

> A pipeable extension of `ls` with SQL querying and file metadata harvesting.

Software dies. Filenames don't.

Every file manager keeps its metadata in a database beside your files. The
database drifts. Files move, records go stale, orphans pile up, and one morning
a catalogue corrupts and takes years of organisation down with it.

ls-sql writes the metadata into the filename instead.

```text
00234-1234567890.png
00234-1234567890^^^ls:hd=20260503^ls:fh=a3f2c8f91b^ls:dw=512^ls:dh=768^^^.png
```

One file, before and after a harvest. Everything ls-sql knows now lives in a
name that Finder shows, Spotlight indexes, and grep reads. There is no database
to keep in sync, because there is no database. The filesystem is the source of
truth and the filename is the cache.

And yes, it is ugly. That is the trade. The filename is doing a job it never
did before, and the price is that you have to look at it. ls-sql earns its keep
where the name was already machine-generated noise, which is where most of
these files start life anyway. On the day you disagree, `reset` puts every
original name back, exactly.

## What it does

- Reads EXIF, ID3, image dimensions, and ZIP contents, then writes them into
  the name.
- Queries them back in SQL: `SELECT * WHERE ex:cam='fujifilm-x-t5'`.
- Prints one full path per line, so the output pipes into anything.
- Hashes the content, so it can tell you when a file changed underneath you.
- Puts the original filename back, exactly, whenever you ask.

Nothing on disk moves until you pass `--commit`. Dry run is the default
everywhere, and it prints what it would have done.

Built for macOS, where the filename ceiling is 255 characters.

## Install

Requires Python 3.14 or newer.

```bash
pipx install "git+https://github.com/east-van-ai/ls-sql.git"
```

For development, clone the repo and `pip install -e . --group dev` in a venv.

## Usage

A command, then a path, then options.

```text
ls-sql <command> PATH [options]
```

Five commands: `list`, `harvest`, `set`, `verify`, and `reset`. The command
goes right after `ls-sql`, and the path right after the command. Run bare
`ls-sql` for the built-in help, or a bare command word such as `ls-sql harvest`
for that command's own.

### The first five minutes

Point `harvest` at a directory. Nothing moves yet.

```bash
ls-sql harvest ~/photos
```

You get a preview: every file it would touch, the name it would get, and a
count at the end. When it reads right, say so.

```bash
ls-sql harvest ~/photos --commit
```

The metadata now lives in the names, and `list` reads it back out.

```bash
ls-sql list ~/photos
```

### Asking questions

```bash
# an exact value
ls-sql list ~/photos --query "SELECT * WHERE ex:cam='fujifilm-x-t5'"

# a tag that is present at all
ls-sql list ~/photos --query "SELECT * WHERE ex:cam IS NOT NULL"

# a substring, here against the image contents of ZIP files
ls-sql list ~/zipped-photos --query "SELECT * WHERE zi:ext CONTAINS 'jpeg'"
```

There is no `FROM` clause, because there is only one thing to query. Add `-R`
to any command to walk subdirectories.

### Checking and undoing

`verify` re-hashes every file and compares the result against the `ls:fh` in
its name. Bit rot, a bad copy, an editor that rewrote the file: all of it shows
up here.

```bash
ls-sql verify ~/photos
```

`reset` strips the harvested tags and puts the original filename back, exactly
as it was. Your own comment on the right of the second `^^^` survives.

```bash
ls-sql reset ~/photos
ls-sql reset ~/photos --commit
```

### Tags of your own

`set` writes tags you choose, in the `ud:` namespace, through `--tags`. Four
operators, and a file that has never been harvested gets harvested first.

```bash
ls-sql set photo.jpg --tags "ud:album=london-2006"   # set a value
ls-sql set photo.jpg --tags "ud:weather+=rainy"      # add one to a list
ls-sql set photo.jpg --tags "ud:weather-=rainy"      # take one away
ls-sql set photo.jpg --tags "ud:weather=="           # drop the tag
```

Carets separate several operations, the same way they separate tags in the
filename. A directory works as well as a single file.

```bash
ls-sql set photo.jpg --tags "ud:album=london-2006^ud:where=thames" --commit
ls-sql set ~/photos --tags "ud:trip=london-2006" --commit
```

You can also pick files by content hash rather than by name. The hash does not
change when the name does, so this reaches a file you have since renamed.

```bash
ls-sql set ~/photos --tags "ud:album=london-2006" --fh "ab2c3d;9fs7g1" --commit
```

### Living in a pipeline

`list` prints one full path per line and nothing else, so it behaves like any
other Unix tool.

```bash
# Count matches
ls-sql list . --query "SELECT * WHERE sd:mn='flux'" | wc -l

# Open results
ls-sql list . | awk '{print $1}' | xargs open

# Grep output directly
ls-sql list . -R | grep "euler-a"
```

A bare `ls-sql` reads paths from stdin, parses the names, and prints them back.
That is passthrough mode, and it is the only time stdin is read at all.

```bash
ls ~/photos | ls-sql
```

With a command word present, stdin is left alone. `ls . | ls-sql harvest .`
ignores the pipe rather than failing, because an inherited pipe, from a shell
pipeline or a Makefile or any subprocess, cannot be told apart from a
deliberate one.

## The filename convention

ls-sql implements **Hatfile**, a metadata convention that lives in the filename
and uses `^^^` as its boundary.

```text
IMG-1234567890-1234567890^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^ls:dw=512^ls:dh=768^ex:dto=2024:07:12^^^mom-at-wedding-1994-06-24.png
^-- original, untouched --^^^--- structured metadata, tagged key-value pairs --------------------------^^^--- human comment ------^
```

Your original filename sits to the left of the first `^^^` and is never
modified. The harvested tags sit between the two boundaries. Anything you want
to say yourself goes to the right of the second one, and ls-sql leaves it
alone. Aim to keep the whole thing under 200 characters.

Tags are namespaced. The four two-letter namespaces belong to the built-in
harvesters, `ud:` is yours, and anything with one letter or three or more is
free for your own tools to claim.

| | | |
| --- | --- | --- |
| ls: | ls-sql native tags | (2-letter, reserved) |
| ex: | EXIF metadata | (2-letter, reserved) |
| au: | Audio metadata | (2-letter, reserved) |
| zi: | ZIP / CBZ metadata | (2-letter, reserved) |
| ud: | User defined custom tags | (blessed user namespace) |

[HATFILE.md](HATFILE.md) has the full convention and every tag in it.

## Albums without an album app

An album is a tag. Number the photos and the running order comes along with it,
and a comment on the end says what you actually thought at the time.

```text
IMG_4520^^^ls:hd=20260503^ls:fh=9b1d4e72ac6a0mha^ex:dto=2006:03:15^ud:2006-london=1^ud:where=palace^^^nice-to-meet-you.jpg
IMG_4521^^^ls:hd=20260503^ls:fh=c3f8a12b916531uj^ex:dto=2006:04:10^ud:2006-london=2^ud:where=thames^^^is-it-raining.jpg
IMG_4522^^^ls:hd=20260503^ls:fh=03754271b00a0e1c^ex:dto=2006:04:15^ud:2006-london=3^ud:where=london-eye^^^you-might-melt-in-rain.jpg
```

No schema, no database, and the album survives being copied to a USB stick.

```bash
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
```

## Finding duplicates

`ls:fh` is a content fingerprint, so two files with the same hash are the same
file whatever they are called.

```bash
ls-sql list . -R --query "SELECT * WHERE ls:fh IS NOT NULL" \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

## What it reads

| | |
| --- | --- |
| JPG | EXIF: camera, date, aperture |
| PNG | Image dimensions |
| GIF | Image dimensions |
| WEBP | Image dimensions |
| MP3 | ID3 tags: artist, album, title |
| M4A | iTunes atoms: artist, album, title |
| ZIP | Entry count, content types |
| CBZ | Comic Book ZIP, same as ZIP |

## Speed

ls-sql reads filenames, not file contents. So the number of files is important,
but the size of your library barely matters.

### File count

| | | |
| --- | --- | --- |
| Casual photographer | 5,000 - 20,000 files | totally normal |
| Serious photographer | 20,000 - 50,000 files | power user |
| SD enthusiast | 10,000 - 30,000 files | reasonable |
| Obsessive SD user | 50,000+ files | okay buddy |
| 100,000 files @ 1MB | ~100GB | you are an enterprise user |

### Drive access speed

| | |
| --- | --- |
| External HDD | ~20,000 files per second |
| External USB SSD | ~50,000 files per second |
| Internal SSD | ~100,000 files per second |

## Who it is for

- Photographers with EXIF-rich libraries
- Small web servers with image collections
- Stable Diffusion and A1111 image generators
- Anyone who lives in Terminal

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ library? You need enterprise tooling and a budget to match.
- Need multi-user, networked, or cloud storage? Same answer.

## Errors

Errors print as `ls-sql: <message>` with a compact usage line. Exit 0 is
success, exit 1 is an ls-sql error, and exit 2 is an argument that argparse
refused. `verify` also exits 1 when it finds changed content, which is an
answer rather than a failure.

Options belong to their command. `--commit` on `list` is an error, not
something quietly ignored.

## Use of AI

This project is built with Artificial Intelligence (AI), deliberately
and in the open. Code and documentation are written in collaboration
with remote and local AI; design decisions, code review, and final
judgement stay human.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

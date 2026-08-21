# ls-sql design & specification

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

## ls-sql Architecture

Five commands, two halves.

```bash
ls-sql harvest .  # reads files, renames them
ls-sql set .      # renames
ls-sql reset .    # renames
ls-sql list .     # reads filenames, never touches a file
ls-sql verify .   # reads and re-hashes, never touches a file
```

Three commands rename, two never do. That distinction is absolute, and it is
the reason dry-run is the default on the first three and meaningless on the
other two.

The filesystem is the only source of truth. There is no database to maintain,
no cache to invalidate, no records to go stale. Everything ls-sql knows lives
in filenames.

## Filename specification

### Hatfile metadata and boundary

`^^^` marks the boundary between the original filename and Hatfile metadata.
This is the Hatfile standard. It is not configurable.

```text
{original_filename}^^^{Hatfile_metadata}^^^{human_comment}.{ext}
```

- Left of the first `^^^` sits the original filename, never modified.
- Between the boundaries sit the tagged key-value pairs.
- Right of the second `^^^` sits a free human comment, and it is optional.
- The trailing `^^^` is always present, even without a comment.
- Aim to keep the whole name under 200 characters.

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

## Tag namespaces

Namespaces keep tags organised and prevent collisions between sources.

```text
au:    audio metadata (MP3, AAC, FLAC, whatever comes next)
ex:    EXIF data
ls:    ls-sql native tags
sd:    Stable Diffusion / A1111 (reserved, not harvested)
ud:    user defined custom tags
zi:    zipfile info (.zip files)
```

### Namespace rules

2-letter namespaces are reserved for ls-sql built-in harvesters. They are short
because they appear in filenames and character budget matters.

- `ud:` is the blessed user namespace for simple custom tags.
- Use 1-letter or 3-letter+ namespaces for your own structured extensions
  (e.g. `myapp:key=value`).
- Use a 2-letter namespace and you are on your own, since harvest will overwrite it.

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

sd:mn    Model name
sd:mh    Model hash
sd:sa    Sampler
sd:sp    Sampling steps
sd:sh    Schedule type
sd:cfg   CFG scale
sd:sd    Seed
sd:la    LoRA

ud:*     Anything that does not overlap with ls-sql native tags
```

### Note on name hash

There is no filename hash tag. You cannot take a hash of a filename that
already contains a hash. The result would never match anything on rebuild.
The file content hash (`ls:fh`) is the stable fingerprint. That is enough.

## Album system

Albums are implemented entirely through user defined tags. No separate data
structure. No database.

[See Granular Details.](#album-system-and-ud-tags)

### Multi select list

[See Granular Details.](#repurpose-album-tags-for-multi-select-list)

## Configuration

There is no configuration file. ls-sql runs on hardcoded defaults, and every
knob it has is a command-line flag.

- Harvest boundary: `^^^`, which is the Hatfile standard and not configurable
- Max filename length: 200 characters
- Fields harvested: all available for the file type

## CLI reference

### CLI grammar

A command word, then a path, then options. vex is the reference implementation
of this grammar; ls-sql keeps one deliberate divergence, piped mode.

```text
ls-sql <command> PATH [options]
```

- **The command is a bare word, and it comes first.** `list`, `harvest`, `set`,
  `verify`, `reset`. It must sit in `sys.argv[1]`, immediately after `ls-sql`,
  not after some flag that happens to parse. There is no default command:
  `ls-sql .` is a usage error, not a listing.
- **The path is a bare word, and it comes second.** Every command acts on one
  directory or file, named in `sys.argv[2]`. `.` for the current directory.
  argparse cannot be trusted with this slot on its own, so the position is
  enforced on a single token. See "Positions are decided, not inferred" below.
- **Options are scoped to their command.** `--ext` and `--max` belong to
  harvest, `--fh` and `--tags` to set, `--query` to list. Passing one to a
  command that has no use for it is an error, not something quietly ignored.
  `--commit`, `--dry-run`, `-R`, and `--verbose` are shared.
- **Bare `ls-sql` prints the banner.** Module docstring to stdout, exit 0.
  Discovering the tool costs nothing and touches nothing.
- **A bare command word is a help request.** `ls-sql harvest`, with nothing
  else on the line at all, prints that command's help and exits 0. Once any
  other argument is present the user has asked for something specific, and
  answering a wrong request with help text would hide the mistake.
- **Neither help path looks at `isatty()`.** What was typed decides the
  answer, not how the process was launched. Gating help on a terminal would
  make `ls-sql harvest` exit 0 from a shell and 1 under `nohup`, cron, or an
  editor, on identical input. The cost is accepted: a scheduled command that
  loses its path argument prints help and exits 0 rather than failing loudly.
- **Piped mode is the exception, and it is the product.** A bare `ls-sql` with
  content on stdin enters passthrough parse mode before argparse runs: read
  paths from stdin, parse the Hatfile names, print full paths, exit 0. Unlike
  the other house CLIs, piped input with no command is not a usage error, it is
  the primary Unix-citizen mode. "Carries content" is a file-type test, not
  `isatty()`. See below.
- **With a command word present, stdin is not an input source.** It is not read
  and it is not an error. See "A pipe cannot be an error here" below.
- **Error style.** Every self-generated error is `ls-sql: <message>` followed
  by the compact USAGE lines, both to stderr, exit 1. Errors never dump the
  full `--help` text.

  ```text
  Usage: ls-sql list|harvest|set|verify|reset PATH [options]
         ls <dir> | ls-sql
  ```

  **Every** means every, including an error where the command line was read
  fine and something the run needed was not there: a path that does not exist,
  a `--query` that will not parse, an `--fh` that matched no file. The usage
  line adds nothing a reader of those needs. It is printed anyway, because
  error output is a contract. One error printing a single line where its
  neighbour prints three reads as a missing print statement rather than as a
  signal, and a reader who has to work out which one it is has been handed a
  puzzle instead of an answer. Uniform output is worth more than the saved
  noise.

  `verify` is not an exception to this. Its exit 1 is a result rather than an
  error, so it carries neither the prefix nor the usage line.

- **Exit codes.** `0` success; `1` every ls-sql-generated error, and `verify`
  when changed content is found (a semantic result rather than an
  error, so the message carries no `ls-sql:` prefix); `2` is reserved for argparse's own
  errors (unknown command, unknown flag, missing value).

  Only `0` and `1` ever come back from `main()`. Argparse hardcodes `2` inside
  `ArgumentParser.error()`, which calls `sys.exit()` itself, so that code
  unwinds past `main()` rather than returning through it. Nothing on argparse's
  public surface names the number or lets it be set, so `2` is a code to assert
  against, never one to produce.

### Positions are decided, not inferred

Both bare words are pinned to a fixed slot, checked directly against `sys.argv`
rather than left to argparse.

Since Python 3.12, argparse back-fills a trailing optional positional from a
token appearing after any number of flags. `ls-sql harvest --commit .` parses
happily with the path set, even though the documented grammar puts the path
immediately after the command. Accepting it would let the real grammar drift
away from the written one, one convenience at a time.

So the path is read from `sys.argv[2]` and nowhere else. A token argparse found
somewhere else on the line is discarded. ls-sql does not go hunting for a path,
and does not guess whether a stray word looks like one.

The command word gets the same treatment for the same reason. argparse resolves
which token is the positional correctly, whatever the interleaving, so a flag
came first exactly when that token is not `sys.argv[1]`.

### main() returns a code, it does not exit

`main()` computes an exit code and returns it. The only `sys.exit()` in the
package is the one wrapping the call, and setuptools already writes that for
the installed `ls-sql` entry point.

The gain is in testing. A returned code is a value a test reads directly, where
`sys.exit()` forces every caller, tests included, to catch a `SystemExit` and
dig the code out of it. Command modules already worked this way and returned
their codes up to the dispatch; `main()` now does the same thing one level up.

The cost is a call site that forgets to `return`. An error helper that prints
and returns a code, called without `return` in front of it, turns a failure
into a silent success. Every helper here is named for what it reports rather
than for ending the process, which is why `_die()` is gone.

### Piped is a file type, not the absence of a terminal

`isatty()` answers "is a human sitting at a terminal". That is not the same
question as "did the user pipe something in", and piped mode depends on the
second one.

The gap between them is `/dev/null`. That is what cron, systemd, `nohup`, CI
runners, and any subprocess with unattached stdin hand a process. Treating
every non-terminal stdin as piped content catches all of those, so a scheduled
harvest reads zero lines, renames nothing, and exits 0. Silent success is the
worst possible failure for a tool that renames files.

Piped mode therefore classifies stdin by file type, via
`os.fstat(sys.stdin.fileno()).st_mode`:

| Type | Example | Content? |
| --- | --- | --- |
| `S_ISFIFO` | `ls . \| ls-sql` | yes |
| `S_ISREG` | `ls-sql < paths.txt` | yes |
| `S_ISSOCK` | socket | yes |
| `S_ISCHR` | terminal, `/dev/null` | no |
| no descriptor | closed stdin, `fstat` raising | no |

`isatty()` still runs first and short-circuits, since a terminal is never piped
content. Checking it first also means a caller that fakes a tty gets the answer
it expects without a real file descriptor behind it.

Note the direction. This is a strict subset of `not isatty()`. Only character
devices leave the set, so nothing newly counts as piped. Sockets stay in
because every non-terminal counted before, and dropping them would regress
anyone feeding one.

Two questions, two tests. Keep them apart:

| Question | Test |
| --- | --- |
| Is a human at a terminal? (banners, prompts, colour) | `isatty()` |
| Did the user pipe content in? (input source) | classify by file type |

### A pipe cannot be an error here

The house rule elsewhere is that a pipe plus an explicit flag is two input
sources and should be an error. That rule does not survive contact with this
grammar, and the reason is worth recording so it does not get "fixed" back.

Every ls-sql command carries a path. If a pipe plus a command were an error,
then any ls-sql call that merely *inherits* a piped stdin would fail:

```bash
printf 'unrelated\n' | sh -c "ls-sql harvest ~/photos"
```

Nothing there aims a pipe at ls-sql. The shell handed the whole pipeline's
stdin to the subshell, and ls-sql inherited it. The same happens inside a
Makefile recipe, a CI step, a `while read` loop, or any subprocess. That is
not a rare corner, it is most scripted use.

A deliberate pipe and an inherited one are the same file descriptor. There is
no signal that separates them, so the error would fire on intent it cannot
see. This is the isatty trap one level up: a test that looks like it measures
user intent but actually measures process plumbing.

So stdin is read in exactly one case, a bare `ls-sql` with nothing else on the
line. With a command word present, stdin is left alone. Not read, not an
error.

The cost is real and accepted: `ls . | ls-sql harvest .` silently ignores the
pipe. The alternative breaks working scripts, which is worse.

It also leaves the door open. Should a command ever read piped paths, it will
need stdin readable alongside a command word, which an error here would have
foreclosed.

### List mode

```bash
ls-sql list .                                        # fresh from filesystem
ls-sql list . -R                                     # recursive
ls-sql list . --query "SELECT * WHERE sd:mn='sdxl'"  # filtered query
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
ls-sql list . --query "SELECT * WHERE zi:ext CONTAINS 'exe'"
```

`list` is the read-only mode and the one that feeds a pipeline. Without
`--query` it prints every parsed row, which is the `ls` in ls-sql.

### Harvest mode

```bash
ls-sql harvest .                         # preview renames, no changes
ls-sql harvest . --commit                # execute renames
ls-sql harvest . --commit -R             # recursive harvest
ls-sql harvest . --commit --ext jpg,png  # filter by extension
ls-sql harvest . --commit --max 50       # limit files per run
```

#### `--max` counts what it actions

`--max N` caps how many files a run harvests. A file that is skipped, for an
extension outside the filter or for a name that carries tags already, is
reported but does not count against N.

The cap holds across the whole walk. It is not a per-directory budget, so a
recursive run renames at most N files no matter how the tree is shaped.

Which files a capped run picks is a separate question, and an open one:
`os.scandir` does not promise an order and ls-sql does not impose one.

### Reset mode

```bash
ls-sql reset ~/photos             # preview strip
ls-sql reset ~/photos --commit    # restore original filenames
ls-sql reset ~/photos --commit -R # recursive
```

Named for what it does to the file, not for the flags it removes. It restores
the original filename exactly.

### Set mode

Write user-defined tags directly into filenames. Harvest-first is automatic.
Dry-run by default. Pass `--commit` to execute.

The tags themselves ride `--tags`, since `set` is now the verb.

```bash
# single file
ls-sql set photo.jpg --tags "ud:album=london-2006"
ls-sql set photo.jpg --tags "ud:album=london-2006" --commit

# multiple tags -- caret-separated
ls-sql set photo.jpg --tags "ud:album=london-2006^ud:where=thames" --commit

# directory -- all files in directory
ls-sql set ~/photos/london --tags "ud:trip=london" --commit

# recursive directory
ls-sql set ~/photos/london --tags "ud:trip=london" -R --commit

# select by content hash
ls-sql set ~/photos --tags "ud:album=london" --fh "ab2c3d,9fs7g1" --commit
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
- `ls:fh` is protected. `set` silently skips it. Content integrity
  is the one thing the tool guards without being asked.

#### Harvest-first

If a file has not been harvested, `set` harvests it first silently, then
applies the tag. The user does not need to run `harvest` first.

#### `--fh` flag

Select files by content hash. Comma-separated list of 16-char SHA256 prefixes.
Hash does not change when the filename changes, so it stays a stable selector
across renames.

```bash
ls-sql set ~/photos --tags "ud:album=london" --fh "ab2c3d4e5f,9fs7g1h2i3" --commit
```

Matches any harvested file whose `ls:fh` value starts with the given prefix.

### Flag rules

- The path is required in every non-piped mode. It names the directory or file
  the command acts on, and it sits right after the command word.
- `harvest` without `--dry-run` or `--commit` defaults to `--dry-run`. Safe always.
- `-R` is recursive, same as `ls -R`.
- `--ext` overrules the whitelisted extensions: jpg, jpeg, png, gif, webp, mp3, m4a, zip, cbz.
- `--query` filters `list` output. The `FROM` clause is omitted, because there is
  only one thing to query.
- `reset` strips everything between the first and second `^^^`. The human
  comment right of the second `^^^` is preserved. Fully reversible.
- `list` output is a clean path per line with no summary, so it pipes into any
  Unix tool as-is. There is no `--quiet`; there is nothing to silence.
- `set` without `--commit` is dry-run. Safe always.
- `--fh` belongs to `set`. It is a file selector, not a query.

## Output style

Output prints full path, pipeable, composable result.

```text
/Users/go/photos/00234^^^ls:hd=20260503^ls:fh=a3f2c8f91b^ls:dw=512^ls:dh=768^^^.png
/Users/go/photos/00891^^^ls:hd=20260503^ls:fh=9b1d4e72ac^ls:dw=1024^ls:dh=1024^^^dog-in-tuxedo.png
```

Pipe it anywhere:

```bash
ls-sql list . -R | grep "dog-in-tuxedo"
ls-sql list . --query "SELECT * WHERE ls:dw='512'" | wc -l
ls-sql list . | awk '{print $1}' | xargs open
```

### Rename previews

Query output is the pipeable half. The three modes that rename files print a
preview instead, and they all print the same shape.

```text
   skipped : note.txt  (extension not in whitelist or --ext list)
   dry-run : photo.jpg
        -> : photo^^^ls:hd=20260805^ls:fh=87428fc522^^^.jpg

2 file(s) dry-run, 1 skipped
  (no files changed -- pass --commit to execute)
```

The status word is right-aligned in a fixed field so the ` : ` column lines up
across every line and every mode. The field is as wide as the longest status
word, which is `restored`. Statuses are `renamed`, `restored`, `updated`, and
`dry-run` for work that happened or would happen, plus `skipped`. Anything not
`skipped` counts toward the actioned total.

Skipped lines appear only under `--verbose`. The reason is in parentheses. The
directory prefix appears only under `-R`, and it applies to every mode that
walks a tree, `--fh` included.

The dry-run hint prints whenever `--commit` was not passed. It is the reminder
that nothing on disk moved.

`verify` is deliberately not this shape. It reports `ok`, `CHANGED`,
and `skipped` against stored hashes, has no rename to preview, and carries its
own summary line. Different question, different output.

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

#### Dependencies are floors, not pins

`[project] dependencies` lists the three packages ls-sql imports, with lower
bounds and no upper caps. A floor is a claim the project can stand behind,
being the version ls-sql was last tested against. A cap would be a claim about
releases that do not exist yet, and that guess strands users on the day Pillow
ships a fine new version.

Exact pins carry a second cost. `pillow==12.2.0` is not a fact about ls-sql. It
collides with every other project in a shared environment that wants a
different Pillow, and it rots once there is no wheel for a new Python.

Reproducibility is a separate problem and wants a separate file. If a release
ever needs byte-identical installs, that is a lock or constraints file applied
at install time, never a permanently narrowed `dependencies`.

#### Both requirements files go away

There is no `requirements.txt` and no `requirements-dev.txt`. `pyproject.toml`
holds runtime packages in `[project] dependencies` and dev tooling in
`[dependency-groups]`. One file, two tables, nothing to keep in sync by hand.

The runtime pair had already drifted, with `pyproject.toml` carrying exact
versions and `requirements.txt` carrying bare names. Nothing checked one
against the other, because nothing can. Two files answering one question is how
that happens.

The dev file went for a different reason. ls-sql is installed with `pipx` and
run, not cloned and contributed to. A requirements file is onboarding
scaffolding for a contributor who does not exist here, and it earns its keep
only in a project that expects one.

Install everything with a single command:

```bash
pip install -e . --group dev
```

Dev tooling goes in `[dependency-groups]` rather than
`[project.optional-dependencies]`. Extras are published metadata: they land in
the wheel, appear on PyPI, and turn `pip install ls-sql[dev]` into a supported
offer. Dev tooling is a fact about the working copy, not about the installed
artifact. Dependency groups stay local and never ship, which is the honest
description of what `ruff` and `black` are to this project.

`--group` needs pip 25.1 or newer. Both the local venv and CI run well past
that, and CI upgrades pip before installing anything.

The dev pins stay exact while the runtime floors do not, and the asymmetry is
deliberate. A pinned `ruff` freezes a rule set, so local and CI agree on what
counts as a lint failure. `pytest` has no rule set to freeze and stays
unpinned.

### Performance targets

- Directory scan 100k files: under 1 second (`os.scandir`)
- Cold start total: under 2 seconds
- Query: linear scan of filenames, no index required at reasonable scale

### Packaging

```toml
[project]
name = "ls-sql"
description = "A pipeable extension of ls with SQL querying and file metadata harvesting."
readme = "README.md"
authors = [{ name = "East Van AI", email = "east-van-ai@proton.me" }]
requires-python = ">=3.14"
license = "MIT"
license-files = ["LICENSE"]
dependencies = ["mutagen>=1.47.0", "piexif>=1.1.3", "pillow>=12.2.0"]

[project.scripts]
ls-sql = "lssql.cli:main"

[dependency-groups]
dev = ["black==26.5.1", "pytest", "pytest-cov", "ruff==0.16.0"]

[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

`version` is omitted above on purpose. A version number copied into this
document goes stale the moment the next release ships, and this one had already
drifted three releases behind.

The setuptools floor is 77 because of PEP 639. The SPDX `license` string and
`license-files` are rejected by older setuptools, which still expects
`license = {text = "MIT"}`.

The `packages.find` block is what makes the src layout explicit rather than
inferred, so a stray top-level directory can never turn into a shipped package.

## What ls-sql does

- Harvests metadata automatically from JPG, PNG, GIF, WEBP, MP3, M4A, ZIP, CBZ
- Carries a human comment, appended to the filename by hand
- Carries user-defined tags for albums, captions, sequences
- Queries with `SELECT * WHERE`, supporting `=`, `CONTAINS`, `IS NOT NULL`,
  and `IS NULL`
- Keeps no database and no cache

That list is the whole tool. Anything not described in this document is not
implemented, however reasonable it sounds.

## Edge cases

When in doubt, warn and skip. Never guess.

- **Malformed caret runs.** The stem is not a Hatfile. See below.
- **Filename exceeds 200 chars.** The harvester warns before renaming, then
  skips the file.
- **File already harvested.** The harvester sees `^^^` and skips. Idempotent.
- **Duplicate files.** `ls:fh` catches identical content whatever the filename.

### What counts as a Hatfile stem

A stem is a Hatfile stem when every one of these holds:

- it splits into at most three parts on `^^^`
- the original part holds no `^`
- the tag part is empty, or splits on `^` into segments that are all non-empty
- the comment part, when present, holds no `^`

Anything else parses as a plain filename, and the write paths skip it.

The tag part needs a clause of its own because `^` is the tag delimiter there.
`ls:hd=20260503^ls:fh=03754271b00a0e1c` is well-formed. A leading caret is not,
because it opens an empty segment.

A run of six carets stays valid. That shape is `original^^^^^^comment`, a
harvested file with an empty tag section. A rule phrased as "every caret run is
exactly three" would reject it by accident.

The rule exists because splitting on `^^^` alone loses data. `str.split` is
greedy from the left, so an odd caret stays glued to the front of the next
field, and `0001-01234^^^^it-is-blue` reads as tags of `^it-is-blue`. That
parses as no tags at all, and `set` then overwrites the tag section and drops
the text:

```text
0001-01234^^^^it-is-blue.png
  -> 0001-01234^^^ud:colour=blue^^^.png
```

`it-is-blue` is gone, and `reset` cannot recover it. The filename is the only
store this project has, so a name it cannot read confidently is a name it must
not rewrite.

A tempting alternative is to treat any run of three or more carets as a
boundary and discard the extras. That guesses, and the guess deletes carets the
user typed.

## When to stop using ls-sql

- More than 10 tags per file? Your problem is bigger than a filename can solve.
- 100GB+ library? You need enterprise tooling and a budget to match.
- Multi-user, networked, or cloud storage? Same answer.

Congratulations. Go get proper gear. 🎣

## Out of scope

- Windows. macOS only.
- Cloud sync or remote filesystems.
- Real-time file watching. Use periodic harvest or cron.
- GUI.
- SQLite. Filenames are the database.

## Granular Details

### `list` mode

Scan a directory and filter files using a SQL-like query against harvested tags
in filenames. No database. Reads filenames directly.

```bash
ls-sql list .
ls-sql list . -R
ls-sql list . --query "SELECT * WHERE sd:mn='sdxl'"
ls-sql list . --query "SELECT * WHERE zi:ext CONTAINS 'exe'"
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
ls-sql list . --query "SELECT * WHERE ls:fh IS NULL"
```

Supports `=`, `CONTAINS`, `IS NOT NULL`, `IS NULL`. Output is full path per
line, pipeable.

### `harvest` mode

Read file metadata and encode it as tagged key-value pairs into the filename.
Dry-run by default. Pass `--commit` to execute. Idempotent: already harvested
files are skipped.

```bash
ls-sql harvest . --dry-run
ls-sql harvest . --commit
ls-sql harvest ~/photos --commit -R
ls-sql harvest . --commit --ext jpg,png
ls-sql harvest . --commit --max 50
```

Supports `--ext` to filter by extension, `--max` to limit files per run,
`-R` for recursive.

### `reset` mode

Strip all harvested tags from filenames and restore originals. Human comments
(right of second `^^^`) are preserved. Dry-run by default. Pass `--commit`
to execute.

```bash
ls-sql reset ~/photos --dry-run
ls-sql reset ~/photos --commit
ls-sql reset ~/photos --commit -R
```

Fully reversible. The original filename left of the first `^^^` is never
modified during harvest, so restoration is lossless.

### `verify` mode

Compare `ls:fh` in filename against current file content hash.

- summary by default, per-file detail with `--verbose`
- exit code non-zero on any mismatch, which makes it scriptable
- read-only, never touches files
- files without `ls:fh` skipped with the reason `no ls:fh -- harvest first`

```bash
ls-sql verify .
ls-sql verify ~/photos -R
```

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

### ZIP files (`zi:`)

ZIP and CBZ files are containers. The metadata worth capturing is what's
inside, not the compression. The ZIP format stores its central directory
separately from compressed data, so filenames are readable without
decompression. No extraction required.

macOS resource forks (`__MACOSX/` and `._` sidecar files) are filtered
automatically. They are implementation noise, not real content. There is no flag to keep them.

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
ls-sql list . --query "SELECT * WHERE zi:dot IS NOT NULL"       # ZIPs with dot entries
ls-sql list . --query "SELECT * WHERE zi:ext CONTAINS 'exe'"    # ZIPs with executables
ls-sql list . --query "SELECT * WHERE zi:cnt IS NOT NULL"       # any harvested ZIP
```

### Stable Diffusion (`sd:`)

Generation parameters written into PNG metadata by A1111 and compatible tools.
The namespace is reserved and the tag names are fixed below, but nothing
harvests them. Listed here so the names are not reused for anything else.

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

### User Defined (`ud:`)

Anything that does not overlap with ls-sql native tags.

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
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL" | sort
```

##### Album rules

- Album name is the `ud:` key. Sequence value is an integer starting at 1.
- One file can belong to multiple albums. Just add more `ud:` tags.
- Albums have no metadata of their own. The filename is the record.
- Sequence gaps are allowed. Order is explicit and human-controlled.

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
ls-sql list ~/recipes --query "SELECT * WHERE ud:ingredients CONTAINS 'beef'"
```

The same pattern works for tags, moods, colours, and keywords, or anything else
you would reach a checkbox list for. One tag key, comma-separated values, no schema required.

### Duplicate detection

`ls:fh` is the stable content fingerprint. Duplicates share the same hash
regardless of filename.

Detect duplicates with a one-liner. No harvester change needed:

```bash
ls-sql list . -R --query "SELECT * WHERE ls:fh IS NOT NULL" \
  | awk -F'[\\^]' '{for(i=1;i<=NF;i++) if($i~/^ls:fh=/) print substr($i,6), $0}' \
  | sort \
  | awk 'prev==$1 {print} {prev=$1}'
```

Prints only files that share a hash with at least one other file.

### `set` mode

`set` is the write side of ls-sql. It encodes user-defined metadata directly
into filenames using the Hatfile tag format.

#### Tag manipulation logic

Given a harvested filename:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=sunny^^^london.jpg
```

**Overwrite** `--tags "ud:tags=rainy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=rainy^^^london.jpg
```

**Append** `--tags "ud:tags+=foggy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=rainy;foggy^^^london.jpg
```

**Remove value** `--tags "ud:tags-=rainy"`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=foggy^^^london.jpg
```

**Delete tag** `--tags "ud:tags-="`:

```text
photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^^^london.jpg
```

#### Multi-value separator

Semicolon `;` is the multi-value separator. Commas are allowed freely in
values, since artist names, album titles, and captions naturally contain
commas.
Semicolon is rare enough in metadata to serve as a clean delimiter. Duplicates
are not allowed, and values are always alphabetically sorted.

```text
ud:tags=foggy;london;sunny
au:al=Simon & Garfunkel, Greatest Hits    # comma in value, fine
```

#### Protected namespaces

2-letter namespaces (except `ud:`) are reserved for ls-sql built-in harvesters.
`set` rejects any operation targeting a reserved namespace and stops with an
error. No files are touched.

```text
ls:fh=abc     error -- ls: is reserved
ex:cam=fuji   error -- ex: is reserved
ud:album=x    allowed -- ud: is the blessed user namespace
myapp:key=x   allowed -- 3-letter+ namespaces are free
```

#### Piping into `set`

`set` does not read paths from stdin. Piping a file list into it does not tag
anything: a bare `ls-sql` is the only invocation that reads stdin, and it
passes paths through unchanged.

```bash
# this prints the list twice over. It does not tag.
ls-sql list ~/photos --query "SELECT * WHERE ex:cam='fujifilm-x-t5'" \
  | ls-sql set --tags "ud:gear=fuji" --commit
```

Combining `list` and `set` in a single invocation is not supported either.
Select with `--fh` or a path, and let dry-run show you what will change.

#### Implementation note

`setter.py` mirrors `scanner.py`, `parser.py`, and `query.py`. Plain nouns, no
prefix. Tag manipulation logic lives there; `cli_set.py` drives it.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and
documentation in this project are written in collaboration with
Artificial Intelligence (AI). The division of labour: the AI explores,
challenges assumptions and edge cases, and drafts; the human
initiates, drafts the designs, explores alongside the AI, reviews
every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

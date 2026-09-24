# ls-sql command surface

The grammar, what each command prints, what each flag decides, and the exit
codes. The model underneath it is in [DESIGN.md](DESIGN.md), and the filename
convention itself is in [HATFILE.md](HATFILE.md).

## CLI grammar

A command word, then a path, then options.

```text
ls-sql <command> PATH [options]
```

- **The command is a bare word, and it comes first.** `list`, `harvest`, `set`,
  `verify`, `reset`. It must sit in `sys.argv[1]`, immediately after `ls-sql`.
  A flag ahead of it is argparse's error, exit 2. There is no default command:
  `ls-sql .` is a usage error, not a listing.
- **The path is a bare word, and it comes second.** Every command acts on one
  directory or file, named in `sys.argv[2]`. `.` for the current directory. One
  path, and nothing behind it: a second bare word is an error, not a token to
  ignore. argparse cannot be trusted with this slot on its own, so the position
  is read off the command line directly. See "Positions are decided, not
  inferred" below.
- **Options are scoped to their command.** Each command has its own parser,
  and it knows only that command's flags. `--ext` and `--max` belong to
  harvest, `--fh` and `--tags` to set, `--query` to list. `--commit` and
  `--dry-run` belong to the three commands that rename, `--verbose` to every
  command but list, and `-R` to all five. Passing a flag to a command that has
  no use for it is argparse's `unrecognized arguments`, exit 2, not something
  quietly ignored.
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
  paths from stdin, parse the Hatfile names, print full paths, exit 0. Piped
  input with no command is not a usage error, it is the primary Unix-citizen
  mode. "Carries content" is a file-type test, not `isatty()`. See below.
- **With a command word present, stdin is not an input source.** It is not read
  and it is not an error. See "A pipe cannot be an error here" below.

### Error style

Every self-generated error is `ls-sql: <message>` to stderr, exit 1. A grammar
error follows the message with the usage line of the command that failed.
Errors never dump the full `--help` text.

```text
$ ls-sql harvest --commit
ls-sql: harvest needs PATH
Usage: ls-sql harvest PATH [--commit] [--ext EXTS] [--max N] [-R] [--verbose]
```

The line belongs to the command, not to the tool. A line naming all five
commands and the pipe describes a grammar nobody asked about. A command typed out
of place, as in `ls-sql --commit harvest .`, still gets its own line, since that
line shows the order it wanted.

Each line names the options its command acts on. `--dry-run` is left off every
one, because it restates the default. The `Usage:` prefix is added when the
error prints, so each command's line is kept bare.

A readiness failure prints the message alone. There the command line was read
fine and something the run needed was not there, so the usage line would answer
a question nobody asked. A path that does not exist is one:

```text
$ ls-sql harvest no-such-path
ls-sql: directory or file not found: no-such-path
```

A `--query` that will not parse is a grammar error, since the query is part of
what was typed, and it keeps the usage line:

```text
$ ls-sql list . --query nonsense
ls-sql: I'm sorry Dave, I can't run that query.
  expected: SELECT * WHERE ...
Usage: ls-sql list PATH [--query QUERY] [-R]
```

An `--fh` prefix that matched no file also prints the usage line.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success, the two help paths included |
| `1` | Any ls-sql-generated error, and `verify` finding changed content |
| `2` | argparse's own errors: unknown command, unknown flag, missing value |

`verify`'s `1` is a semantic result rather than a failure, so its message
carries neither the `ls-sql:` prefix nor the usage line.

Only `0` and `1` ever come back from `main()`. Argparse hardcodes `2` inside
`ArgumentParser.error()`, which calls `sys.exit()` itself, so that code unwinds
past `main()` rather than returning through it. Nothing on argparse's public
surface names the number or lets it be set, so `2` is a code to assert against,
never one to produce.

### Positions are decided, not inferred

Both bare words are pinned to a fixed slot. The path is read off `sys.argv`
directly, and the parser holds the command word.

Since Python 3.12, argparse back-fills a trailing optional positional from a
token appearing after any number of flags. `ls-sql harvest --commit .` parses
happily with the path set, even though the documented grammar puts the path
immediately after the command. Accepting it would let the real grammar drift
away from the written one, one convenience at a time.

So the path is read off the front of the command line and nowhere else.
`leading_paths()` walks the tokens after the command and returns the run of bare
words ahead of the first flag. The path is the first of them. What argparse
resolved is never consulted. ls-sql does not go hunting for a path, and does not
guess whether a stray word looks like one.

Reading the whole run, rather than one token, is what makes a second bare word
answerable. `ls-sql harvest . extra` is ls-sql's own error, exit 1, and it names
`extra`. Left to argparse it is `unrecognized arguments`, exit 2, which reports
the token without saying what the grammar wanted in its place. The parser
therefore runs through `parse_known_args()`, so the leftover survives to reach
that check. A leftover that starts with a dash goes straight back to argparse,
which names a misspelled flag better than ls-sql can.

The command word needs no such reading. The top-level parser knows none of the
commands' flags, so any flag ahead of the command word is argparse's
`unrecognized arguments`, exit 2. A command word that parses is `sys.argv[1]`.
A flag belonging to another command is exit 2 for the same reason: the
command's own parser has never heard of it.

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

A pipe plus an explicit flag is two input sources, which usually makes it an
error. That rule does not survive contact with this grammar.

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
line. With a command word present, stdin is left alone. Not read, not an error.

The cost is real and accepted: `ls . | ls-sql harvest .` silently ignores the
pipe. The alternative breaks working scripts, which is worse.

It also leaves the door open. Should a command ever read piped paths, it will
need stdin readable alongside a command word, which an error here would have
foreclosed.

## list

Read-only, and the command that feeds a pipeline. It scans filenames and
filters them with a SQL-like query against the harvested tags. Without
`--query` it prints every parsed row, which is the `ls` in ls-sql.

```bash
ls-sql list .
ls-sql list . -R
ls-sql list . --query "SELECT * WHERE ex:cam='fujifilm-x-t5'"
ls-sql list . --query "SELECT * WHERE zi:ext CONTAINS 'exe'"
ls-sql list ~/photos --query "SELECT * WHERE ud:2006-london IS NOT NULL"
ls-sql list . --query "SELECT * WHERE ls:fh IS NULL"
```

The predicates are `=`, `CONTAINS`, `IS NOT NULL`, and `IS NULL`. There is no
`FROM` clause, because there is only one thing to query. Output is a full path
per line.

## harvest

Read file metadata and encode it as tagged key-value pairs into the filename.
Dry-run by default. Pass `--commit` to execute. Idempotent: a name that already
carries `^^^` is skipped.

```bash
ls-sql harvest .                         # preview renames, no changes
ls-sql harvest . --commit                # execute renames
ls-sql harvest . --commit -R             # recursive harvest
ls-sql harvest . --commit --ext jpg,png  # filter by extension
ls-sql harvest . --commit --max 50       # limit files per run
```

`--ext` overrules the whitelisted extensions: jpg, jpeg, png, gif, webp, mp3,
m4a, zip, cbz.

### `--max` counts what it actions

`--max N` caps how many files a run harvests. A file that is skipped, for an
extension outside the filter or for a name that carries tags already, is
reported but does not count against N.

The cap holds across the whole walk. It is not a per-directory budget, so a
recursive run renames at most N files no matter how the tree is shaped.

Which files a capped run picks is not specified. `os.scandir` does not promise
an order, and ls-sql does not impose one.

## set

Write user-defined tags directly into filenames. The tags ride `--tags`, since
`set` is the verb. Dry-run by default.

```bash
# single file
ls-sql set photo.jpg --tags "ud:album=london-2006"
ls-sql set photo.jpg --tags "ud:album=london-2006" --commit

# multiple tags, caret-separated
ls-sql set photo.jpg --tags "ud:album=london-2006^ud:where=thames" --commit

# every file in a directory, then the same recursively
ls-sql set ~/photos/london --tags "ud:trip=london" --commit
ls-sql set ~/photos/london --tags "ud:trip=london" -R --commit

# select by content hash
ls-sql set ~/photos --tags "ud:album=london" --fh "ab2c3d,9fs7g1" --commit
```

### Operators

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

Against `photo^^^ls:hd=20260504^ls:fh=ab2c3d4e5f^ud:tags=sunny^^^london.jpg`:

```text
--tags "ud:tags=rainy"     -> ...^ud:tags=rainy^^^london.jpg
--tags "ud:tags+=foggy"    -> ...^ud:tags=foggy;rainy^^^london.jpg
--tags "ud:tags-=sunny"    -> ...^ls:fh=ab2c3d4e5f^^^london.jpg
--tags "ud:tags=="         -> ...^ls:fh=ab2c3d4e5f^^^london.jpg
```

### Operator rules

- Overwrite (`=`) works on any tag, any namespace `set` will accept.
- Append (`+=`) and remove (`-=`) work on any tag. No babysitting. Harvest will
  overwrite machine-generated tags on the next run anyway.
- Values are semicolon-separated, deduplicated, and sorted alphabetically.
- A tag left empty by `-=` is removed entirely. Empty tags are noise.
- `ls:fh` is protected. `set` silently skips it. Content integrity is the one
  thing the tool guards without being asked.
- Every other 2-letter namespace is reserved for the built-in harvesters, and
  `set` refuses the whole run rather than touching a file. `ud:` is the blessed
  user namespace, and anything with one letter or three or more is free.

### Harvest-first

If a file has not been harvested, `set` harvests it first silently, then
applies the tag. The user does not need to run `harvest` first.

### `--fh` selects by content hash

A comma-separated list of `ls:fh` prefixes, each up to the full 16 characters.
The hash does not change when the filename changes, so it stays a stable
selector across renames. A file matches when its `ls:fh` value starts with one
of the prefixes. Every prefix is measured on its own length, so a short one and
a long one sit on the same line without interfering.

`--fh` belongs to `set`. It is a file selector, not a query.

### Every `--fh` prefix has to find a file

A prefix that matches nothing stops the run. The error names each prefix that
found nothing, and no file is renamed, the files that did match included.

`--fh` is a list of files the user believes are on disk. A prefix that finds
none of them means one of those beliefs is wrong, and nothing on the command
line says which way: a typo, a file already moved, a hash copied out of another
directory. Renaming the rest and exiting 0 would report a batch as landed when
part of it never ran.

One rule then covers the whole flag. A run where every prefix misses already
stopped with an error. A run where one prefix in three misses is the same
situation, and answering it differently would tie the exit code to how many
prefixes happened to be right.

An `--fh` with no prefix in it, empty or only separators, is an error too. An
empty value is what `--fh "$HASH"` passes when the lookup found nothing, and
reading it as no selector at all would tag every file under PATH.

### `set` does not read stdin

A pipe into `set` is ignored, as it is for every command. `set` acts on its
PATH as usual, and without one it is a usage error. Select with `--fh` or a
path, and let dry-run show what will change.

## verify

Compare the `ls:fh` in each filename against the file's current content hash.
Read-only, and it never renames.

```bash
ls-sql verify .
ls-sql verify ~/photos -R
```

Summary by default, per-file detail with `--verbose`. A file with no `ls:fh` is
skipped with the reason `no ls:fh -- harvest first`. Changed content exits 1,
which is what makes it scriptable.

## reset

Strip the harvested tags and restore the original filename exactly. The human
comment right of the second `^^^` is preserved. Dry-run by default.

```bash
ls-sql reset ~/photos             # preview strip
ls-sql reset ~/photos --commit    # restore original filenames
ls-sql reset ~/photos --commit -R # recursive
```

Named for what it does to the file, not for the flags it removes. Restoration
is lossless, because the original filename left of the first `^^^` is never
modified during harvest.

## Shared flags

- `-R` is recursive, same as `ls -R`.
- `--commit` executes. Dry-run is the default on `harvest`, `set`, and `reset`,
  and `--dry-run` wins if both are passed.
- `--verbose` adds the skipped lines to a rename preview, and per-file detail
  to `verify`. `list` has nothing to skip and does not take it.
- There is no `--quiet`. `list` output is a clean path per line with no summary,
  so there is nothing to silence.

## Output style

`list` prints a full path per line, and nothing else. That is the pipeable half.

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

The three commands that rename files print a preview instead, and all three
print the same shape.

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

`verify` is deliberately not this shape. It reports `ok`, `CHANGED`, and
`skipped` against stored hashes, has no rename to preview, and carries its own
summary line. Different question, different output.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and documentation in
this project are written in collaboration with Artificial Intelligence (AI). The
division of labour: the AI explores, challenges assumptions and edge cases, and
drafts; the human initiates, drafts the designs, explores alongside the AI,
reviews every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

MIT License · Copyright (c) 2026 Go Nakamaru

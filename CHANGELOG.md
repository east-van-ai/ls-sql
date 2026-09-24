# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.16.2] - 2026-09-24

### Changed

- A missing PATH reads `harvest needs PATH`, in the wording the stray-word error
  already uses.
- Each command has its own parser, `version` included. A flag it does not take is
  argparse's `unrecognized arguments`, exit 2, not 1, and so is any flag before the
  command word.
- `list` no longer accepts `--verbose`, which it ignored.
- `ls-sql -h` lists the commands, and `ls-sql <command> -h` shows only its flags.

## [0.16.1] - 2026-09-18

### Changed

- The shipped documents move to `docs/`: DESIGN.md, HATFILE.md, and RESULTS.md.
- DESIGN.md splits in two. It keeps the model, and the new `docs/CLI.md` takes the
  grammar, the commands, the flags, the output shapes, and the exit codes.
- A path that does not exist prints the error message alone, with no usage line.

### Fixed

- An error prints the usage line of the command that failed.
- The docs list only the tags ls-sql harvests, and scope `--ext` to `harvest`.
- An empty `--fh` is an error, instead of tagging every file under PATH.

## [0.16.0] - 2026-09-01

### Added

- `ls-sql version` prints the installed version, the same line `--version`
  prints. A word or a flag after it is an error, exit 1.
- `RESULTS.md`, a benchmark over 1,048,576 files measuring ls-sql against
  `find`, ripgrep, and SQLite, on flash and on a spinning disk. It ships with
  the `tools/` scripts that build the corpus, so the run can be repeated.

### Changed

- Neither version spelling is advertised. The banner's option list, README, and
  DESIGN no longer mention `--version`.
- `set --fh` refuses the whole run when a prefix matches no file, and names
  that prefix. It used to rename whatever the other prefixes found and exit 0.
- DESIGN.md carries decisions only and working notes are gone.
- `zi:dir` joined the tag reference it was already being harvested into.
- README's Speed section carries measured numbers in place of estimates, and
  now says which commands read bytes and which only read names.
- HATFILE gained "Any tool can read it": one query answered by ripgrep, `find`,
  and ls-sql alike, none of which has heard of the convention.

### Fixed

- `set --fh` matches every prefix on its own length. Prefixes of different
  lengths on one line used to leave some silently dead, so the run renamed
  fewer files than asked and still reported success.
- The harvest skip reason names the stem instead of the filename. It always
  measured the stem, so a 79-character stem still harvests behind a
  five-character extension, which the old wording denied.
- The documented length rule matches the code.
- Stale examples in DESIGN.md are updated.
- README's `--fh` example separates hashes with commas.

## [0.15.2] - 2026-08-23

### Added

- `ls-sql --version` prints the installed version and exits 0. Argparse's
  version action carries it, so it answers wherever it sits on the line, and
  the command it was given never runs.

### Changed

- A second bare word after PATH is now ls-sql's own error, exit 1, and it names
  the stray token. Argparse used to answer it with `unrecognized arguments`,
  exit 2.

## [0.15.1] - 2026-08-21

### Changed

- `pyproject.toml` is the only place dependencies are declared. Runtime
  packages sit in `[project] dependencies` as floors instead of exact pins;
  dev tooling moved to `[dependency-groups]`, which never ships in the wheel.
  Install with `pip install -e . --group dev` (needs pip 25.1 or newer).
- `pyproject.toml` gained the packaging metadata it was missing: `description`,
  `readme`, `authors`, `license`, `license-files`, an explicit `[build-system]`
  on `setuptools>=77` for PEP 639, and `[tool.setuptools.packages.find]`.
- README, DESIGN, and HATFILE rewritten for the ear. The README opens on a
  filename before and after a harvest instead of a feature list, reference
  blocks became tables, and the dash-as-conjunction habit is gone throughout.
- Duplicated logic folded together. `list` takes its file-or-directory
  dispatch from `shared.resolve()`, the three places that assembled
  `original^^^tags^^^comment.ext` by hand call `parser.join_hatfile_name()`,
  one `scanner.walk_files()` replaced five directory walkers, and `SEPARATOR`
  is declared once, in `parser.py`.

### Removed

- RELEASING.md. Nothing in it was specific to ls-sql, and the stable-branch
  model it described is already gone.
- ROADMAP.md. It never shipped with a release, and unbuilt ideas are now
  tracked outside the repo.
- The five-line banner comment repeated at the top of every source and test
  file. `cli.py` keeps its own: that one is the banner a bare `ls-sql` prints.
- `requirements.txt` and `requirements-dev.txt`.

### Fixed

- `--max` caps a whole harvest run again. The limit was handed to each
  subdirectory as a budget minus the files already seen, skipped ones
  included, so a recursive `--max 2` could rename five files, one, or none
  depending on how many unrelated files preceded a subdirectory. It now counts
  the files a run actions, once, across the whole walk, and the files it skips
  are reported rather than dropped.
- `set` names `--tags` in the errors it raises about its payload. Three of
  them still said `--set`, the flag v0.15.0 renamed, so the message pointed at
  a flag the user could not have typed.
- `set` no longer destroys filename text on a stem whose caret run is not a
  multiple of three. `0001-01234^^^^it-is-blue.png` lost `it-is-blue`, and
  `reset` could not recover it. Such a stem is not a Hatfile and the write
  paths now skip it.
- `harvest` no longer turns a seven-caret stem into a four-caret one.
- Rename previews no longer double the separator when the path is given with a
  trailing slash, which is what tab completion produces.
- The CI workflow ships with the public release again. `.weed-out-ignore`
  matches `.github/**/*.yaml`, but the file was named `ci.yml`, so it was
  being weeded out.

## [0.15.0] - 2026-08-06

The version line returns to `0.x`, resuming after `v0.14.1`. The `v1.0.0` and
`v1.1.0` tags stay in git history; they were premature.

### Changed

- **Breaking: the CLI takes a command word and a positional path.**
  `ls-sql <command> PATH [options]`, with `list`, `harvest`, `set`, `verify`,
  and `reset` replacing the mode flags. `--target` is gone, `--remove-all-tags`
  is now `reset`, and the `--set` payload moved to `--tags`. `ls-sql .` is a
  usage error: there is no default command.
- The command word must be the first argument and the path the second. Neither
  slot is filled from a token appearing later on the line.
- Options are scoped to their command. `list PATH --commit` and
  `harvest PATH --query ...` are errors now, not silently ignored.
- A bare command word prints that command's help and exits 0, whatever stdin
  is. Help used to be gated on `isatty()`, so the same command answered
  differently from a shell than under `nohup`, cron, or an editor.
- Piped passthrough happens only for a bare `ls-sql`. With a command word
  present, stdin is neither read nor an error.
- `cli.py` split into `cli_list`, `cli_harvest`, `cli_set`, `cli_verify`,
  `cli_reset`, and `cli_util`. `harvest`, `set`, and `reset` share one preview
  printer, documented in `DESIGN.md` and pinned by
  `tests/test_cli_output_format.py`.
- Consolidated duplicated logic behind `parser.should_skip()` and
  `harvester_util.tags_to_string()`.

### Fixed

- Piped mode is entered only when stdin actually carries content: a pipe, a
  redirect, or a socket, classified by file type rather than by
  `not isatty()`. Unattended runs get `/dev/null` on stdin, so a scheduled
  harvest used to pass through, rename nothing, and exit 0.
- Directory walks in `harvest`, `reset`, and `verify` now skip trailing-dot
  filenames (e.g. `foo.`) consistently with every other mode.
- Rename previews line up on the same status column in every mode. `reset`
  padded to 8 characters and the others to 7, so one status word printed at
  two different indents.
- `set --fh -R` shows each match's directory prefix, like every other recursive
  mode. Files sharing a basename across directories were indistinguishable in
  the preview.

## [1.1.0] - 2026-07-19

### Fixed

- `pipx install` now works with git+https: pinned runtime dependencies are
  declared in `pyproject.toml` `[project] dependencies`. Previously it failed
  at startup with the `pysqlite3` install hint.

### Added

- RELEASING.md -- stable-branch release model; `pipx install` from `@stable`
- `.claude/settings.json` with house permission rules

### Changed

- BREAKING: the target directory/file is now passed with a required `--target` flag; the positional form (`ls-sql .`) is removed. Explicit flags make invocations self-describing for AI agents and let permission guardrails match reliably on `--target`.
- CLI grammar aligned with the mdmap house style: bare `ls-sql` on a TTY now prints the built-in help banner and exits 0 (was: missing-`--target` error, exit 1); errors print as `ls-sql: <message>` plus a compact usage line instead of dumping the full `--help` text; piped passthrough mode is unchanged by design
- DESIGN.md gained a "CLI grammar" section; README restructured to the house heading order with new Example output and Install sections; stale `--quiet` references removed and the `--set` pipe pattern marked as not yet implemented (V2)
- CI always runs (changed-files gating removed) and lints with ruff in addition to black
- `requirements.txt` and `requirements-dev.txt` are now not including the pinned versions
- README quick start gained tag-presence (`IS NOT NULL`) and `CONTAINS` query examples
- Planned-feature references say v1.x instead of v1.1; install URL points at the east-van-ai org

## [1.0.0] - 2026-05-19

### Added

- Standardized comments across the codebase

### Changed

- Updated documents for public release

## [0.14.1] - 2026-05-14

### Added

- ls:dw and ls:dh -- image width and height as separate tags, replaces ls:res

### Changed

- ls:fh hash prefix extended from 10 to 16 characters
- semicolon is now the standard delimiter for --fh and --ext args; comma still accepted for both
- HATFILE.md updated to reflect new tag definitions

## [0.14.0] - 2026-05-13

### Added

- tests: ensure hidden files are ignored in any operation mode
- tests: ensure --set mode --fh option works
- tests: ensure pipe operation works
- docs: NOTES.md -- running scratchpad for doc updates and decisions

### Changed

- refactor: --fh logic extracted from main() into run_set_mode()
- refactor: --query logic extracted from main() into run_query_mode()

## [0.13.0] - 2026-05-12

### Added

- Support for passing filename as an argument in addition to directory name across all CLI modes:
  --query mode
  --harvest mode
  --remove-all-tags mode
  --verify mode
  --set mode

### Changed

- Improved error handling to ensure errors are printed to standard error
- Added explicit sys.exit(0) on successful CLI completion
- Removed initial restriction preventing filename as argument by implementing proper support

## [0.12.0] - 2026-05-08

### Added

- `--set` -- write user-defined tags directly into filenames
  - operators: `=` overwrite, `+=` append, `-=` remove value, `==` delete tag
  - empty value is always a no-op -- safe by design
  - `==` with value present is a no-op -- delete must be explicit
  - harvest-first -- automatic if file not yet harvested
  - file or directory target, recursive with `-R`
- `--fh` -- select files by content hash prefix (comma-separated)
- `setter.py` -- new module for set mode logic

### Changed

- 2-letter namespaces (except `ud:`) are protected in `--set` mode

## [0.11.0] - 2026-05-05

### Added

- GitHub Actions CI -- black and pytest on push and pull request to main
  - subprocess tests skipped on Linux CI -- stdout capture unreliable on GitHub Actions

### Changed

- multi-value separator: `;` (semicolon) -- comma is allowed freely in values
  - `zi:ext` delimiter migrated from comma to semicolon
  - semicolons sanitized in `au:` tag values

### Docs

- design --set functionality
- update ROADMAP for v0.11.x --set arc

## [0.10.0] - 2026-05-04

### Added

- default harvest extension whitelist -- jpg, jpeg, png, gif, webp, mp3, m4a, zip, cbz
- unknown extensions require explicit `--ext` opt-in

### Changed

- duplicate detection documented -- `ls:fh` one-liner, no harvester change needed
- namespace rules documented -- 2-letter reserved for ls-sql, `ud:` blessed for users
- sv: namespace parked as post-v1 candidate in ROADMAP
- 80-char original stem limit added to HATFILE.md Rules section
- `capture=sys` rationale documented in pyproject.toml

## [0.9.0] - 2026-05-04

### Added

- warn and skip if original filename stem exceeds 80 characters
- warn and skip files with carets in original filename
- sanitize metadata values replacing carets with dashes
- full round-trip validation -- harvest, remove-all-tags, validate

## [0.7.5] - 2026-05-02

### Added

- `--verify` -- compare `ls:fh` in filename against current file content hash
  - summary by default, per-file detail with `--verbose`
  
## [0.7.4] - 2026-05-01

### Added

- M4A -- `au:ar`, `au:al`, `au:tt`, `au:tn`, `au:yr` via mutagen MP4
- ZIP, CBZ -- `zi:cnt`, `zi:ext`, `zi:dot`, `zi:dir` via zipfile stdlib
  - macOS resource forks (`__MACOSX/`, `._` files) filtered

## [0.7.3] - 2026-05-01

### Added

- `--verbose` -- skipped files hidden by default, shown with the verbose flag

## [0.7.2] - 2026-04-28

### Changed

- rename `main.py` to `cli.py`
- move utility functions and constants to `harvester_util.py`
- revise `DESIGN.md` for v1 scope

## [0.7.1] - 2026-04-28

### Added

- add `HATFILE.md` -- the Hatfile specification

### Changed

- trailing hat always -- new filenames are always appended with  `^^^` even with no comment
- update `DESIGN.md`
  - remove stale config section
  - introduce: Hatfile standard decision, Granular Details section, Table of Contents
- revise ROADMAP -- split v0.7.1 into subsequent patches

## [0.7.0] - 2026-04-27

### Added

- MP3 -- `au:ar`, `au:al`, `au:tt`, `au:tn`, `au:yr` via mutagen
- JPG -- `ex:dto`, `ex:cam`, `ex:iso`, `ex:ap`, `ex:fl` via piexif
- Resolution -- `ls:res` for JPG, PNG, GIF, WEBP

## [0.8.0] - 2026-04-26

### Added

- `--query "SELECT * WHERE ls:hd = '20260426'"` parsed and evaluated
- filter `list[dict]` against tag predicates
- support `IS NOT NULL`, `=`, `CONTAINS`
- recursive `-R` mode wired in

## [0.6.4] - 2026-04-25

### Added

- `--ext` -- harvest files with specific extensions

### Changed

- `--max` -- count only harvestable/harvested files (skip “skipped” entries)

## [0.6.3] - 2026-04-24

### Added

- ls:fh tag -- displays the hash of a file’s content.

### Changed

- ls: tag handling -- logic moved out of the main module into a harvester_ls file.

## [0.6.2] - 2026-04-24

### Added

- add `--max N` -- maximum number of harvest at once
- prevent processing of problematic filenames
- sort process results by directory and filename

### Fixed

- resolved unpredictability in `--harvest` and `--remove-all-tags`
- fixed display handling for `--harvest` and `--remove-all-tags`
- corrected recursive handling in `--remove-all-tags`

## [0.6.1] - 2026-04-23

### Dev

- enable `--remove-all-tags` with `--dry-run` and `--commit`

## [0.6.0] - 2026-04-22

### Dev

- harvester scaffold -- save file metadata in filenames

### Added

- add ls:hd harvest date
- `--dry-run` mode by default, `--commit` to execute
- Skip already-harvested files (idempotent)
- detect and avoid non-existent path

## [0.5.0] - 2026-04-21

### Changed

- output is full path per line -- ls convention corrected, size and date removed
- scanner returns dicts, FileRow class removed
- path key holds directory only, filename excluded
- alphabetical order as default output in standalone mode

### Added

- filename key in parsed dict -- raw system filename, reconstruction is lossy
- skip files without extensions
- skip hidden files
- guard against ^^^ in directory path in piped mode

### Fixed

- ex:dto tag casing corrected in DESIGN doc

## [0.4.0] - 2026-04-20

### Dev

- directory scanner -- scan, filter, parse, and output structured rows

## [0.3.0] - 2026-04-19

### Dev

- filename parser -- extract structured data from plain and hatfile filenames
- round-trip test -- parse then reconstruct equals original
- src/ layout requires `pip install -e .` for local imports to resolve

## [0.2.0] - 2026-04-18

### Added

- first pipeline -- ls output piped through Python
- dev environment setup with pyenv and venv
- black formatter

## [0.1.0] - 2026-04-17

### Added

- README and DESIGN -- project charter and initial specification

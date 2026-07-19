# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [v1.1.0] - 2026-07-19

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

## [v1.0.0] - 2026-05-19

### Added

- Standardized comments across the codebase

### Changed

- Updated documents for public release

## [v0.14.1] - 2026-05-14

### Added

- ls:dw and ls:dh -- image width and height as separate tags, replaces ls:res

### Changed

- ls:fh hash prefix extended from 10 to 16 characters
- semicolon is now the standard delimiter for --fh and --ext args; comma still accepted for both
- HATFILE.md updated to reflect new tag definitions

## [v0.14.0] - 2026-05-13

### Added

- tests: ensure hidden files are ignored in any operation mode
- tests: ensure --set mode --fh option works
- tests: ensure pipe operation works
- docs: NOTES.md -- running scratchpad for doc updates and decisions

### Changed

- refactor: --fh logic extracted from main() into run_set_mode()
- refactor: --query logic extracted from main() into run_query_mode()

## [v0.13.0] - 2026-05-12

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

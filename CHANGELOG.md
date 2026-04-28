# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.7.2] - 2026-04-28

### Changed

- rename `main.py` to `cli.py`
- move utility functions and constants to `harvester_util.py`
- revise `DESIGN.md` for v1 scope

## [0.7.1] - 2026-04-28

### Added

- add `HATFILE.md` -- the Hatfile specification

### Changed

- update `DESIGN.md`
  - trailing hat always -- new filenames are always appended with  `^^^` even with no comment
  - remove stale config section
  - introduce: Hatfile standard decision, Granular Details section, Table of Contents

- revise ROADMAP -- split v0.7.1 into subsequent patches

## [0.7.0] - 2026-04-27

### Added

- MP3 -- `au:ar`, `au:al` via mutagen
- JPG -- `ex:dto`, `ex:cam`, `ex:iso`, `ex:ap`, `ex:fl` via piexif
- Resolution -- `ls:res` for MP3, JPG, PNG, GIF, WEBP

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

- enable --remove-all-tags with --dry-run and --commit

## [0.6.0] - 2026-04-22

### Dev

- harvester scaffold -- save file metadata in filenames

### Added

- add ls:hd harvest date
- Dry-run mode by default, `--commit` to execute
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

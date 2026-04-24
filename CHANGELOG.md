# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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

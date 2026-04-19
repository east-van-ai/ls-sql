# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- README and DESIGN -- project charter and initial specification

## [0.2.0] - 2026-04-18

### Added
- first pipeline -- ls output piped through Python
- dev environment setup with pyenv and venv
- black formatter

## [0.3.0] - 2026-04-19

### Dev
- filename parser -- extract structured data from plain and hatfile filenames
- round-trip test -- parse then reconstruct equals original
- src/ layout requires `pip install -e .` for local imports to resolve

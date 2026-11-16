# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

### Changed

- Adopt the palewire/python-open-source-template tooling: uv, Ruff, ty, pytest,
  a Makefile and updated workflows. The minimum supported Python is now 3.11.

### Fixed

- Print valid JSON from the `active-perimeters` and `incidents` commands. They
  previously printed a Python dictionary with single quotes, which JSON tools
  could not read.

### Removed

- Remove the Pipfile in favor of `pyproject.toml` and `uv.lock`.

### Security

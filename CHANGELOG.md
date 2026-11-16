# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Add a `get` setting to every download function, so callers can make requests
  with their own function.
- Add `get_active_perimeters_last_edited` and `get_incidents_last_edited`,
  which report when NIFC last edited each layer so callers can skip a download
  when nothing has changed.
- Add `where`, `out_fields` and `geometry_precision` settings to
  `get_active_perimeters` and `get_incidents`, and matching `--where`,
  `--out-fields` and `--geometry-precision` command-line options. The defaults
  keep the old behavior.
### Changed

- Adopt the palewire/python-open-source-template tooling: uv, Ruff, ty, pytest,
  a Makefile and updated workflows. The minimum supported Python is now 3.11.

### Fixed

- Check the data NIFC sends back with Pydantic: the shape of every feature, the
  geometry type for each layer, whole-number feature IDs, and the paging flag.
  A download that sees the same feature twice, which happens when NIFC edits its
  data while pages are being read, starts over up to three times before
  raising `NIFCError`. Settings such as an empty `where` or a negative
  `geometry_precision` are rejected before any request is made.
- Download every page of results. NIFC returns at most 2,000 features per
  request, and anything beyond that was silently left out.
- Raise a clear `NIFCError` when NIFC replies with an error message, invalid
  JSON or something other than a list of features. Before, an error message
  inside a successful reply was returned as if it were fire data.
- Print valid JSON from the `active-perimeters` and `incidents` commands. They
  previously printed a Python dictionary with single quotes, which JSON tools
  could not read.

### Removed

- Remove the Pipfile in favor of `pyproject.toml` and `uv.lock`.

### Security

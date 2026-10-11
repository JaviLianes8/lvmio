# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `parse_lvm(text)` parses a `.lvm` string already in memory; `read_lvm` delegates
  to it.
- `Channel.time_axis()` returns the X axis (`x0 + i * delta_x`), one value per
  sample. `Channel` is now sized and iterable.
- `Segment` supports access by channel name (`segment["Voltage"]`, `get`, `in`),
  `names`, `len` and iteration over its channels. `LvmFile` supports `len` and
  iteration over its segments.
- An `lvmio` console command (`header`, `channels`, `dump`, `--version`) to inspect
  a file and export a channel or a whole segment as CSV or JSON.
- Golden fixtures of genuine LabVIEW output and a cross-check test against the
  `lvm_read` package.

### Changed

- `Channel`, `Segment` and `LvmFile` are now frozen dataclasses.

### Fixed

- Real `X_Columns=No` files keep an empty leading X column; the reader no longer
  reads the first channel from it and shifts every signal by one.
- Empty data cells now parse to `float('nan')` instead of being dropped, keeping
  each channel aligned with its own time axis.

## [0.1.0]

- First release.
- `write_lvm` serialises channels to a spec-faithful `.lvm` file, filling the
  writer gap that existing readers leave open.
- `read_lvm` parses the file header and data segments back into typed objects.
- `Channel`, `Segment` and `LvmFile` model the format; `LvmError` reports invalid
  input.
- Supports Tab and Comma separators, a configurable decimal separator, multiple
  segments, and `X_Columns` set to `One` or `No`.

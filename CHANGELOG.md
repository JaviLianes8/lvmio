# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-14

The public API is now stable: `Channel`, `Segment`, `LvmFile`, `LvmError`, `parse_lvm`,
`read_lvm`, `format_lvm` and `write_lvm`, and the `lvmio` command. Reading and writing follow
files that LabVIEW 2026 wrote and read; the guide describes the format and the upgrade.

### Added

- `format_lvm(data, ...)` returns the text that `write_lvm` writes.
- `x_columns` argument for the writer; `X_Columns` `Multi` is read and written.
- `encoding` argument for `read_lvm` and `write_lvm`; `read_lvm` reads Windows-1252 files,
  which LabVIEW writes on Western-European Windows systems.
- `Segment.comment`, the comment of a data set.
- `python -m lvmio`, and `--encoding` on every command.

### Changed

- Samples are written in LabVIEW's number format (fixed notation from 1e-4 to 1e7, exponent
  notation otherwise, `NaN`, `Inf`, `-Inf`); `X0` keeps 17 significant digits.
- The file layout matches LabVIEW's writer: `X_Value` always heads the column line, header
  lines are padded the same way, `Y_Unit_Label` is left out when no channel has a unit, and
  a line with the separator follows the file header.
- `LvmFile.multi_headings` is a field read from the file instead of a property computed from
  the number of segments. The writer still writes `Yes` for more than one segment.
- A number cell must be a number in full: `1_0`, `0x10`, `2.5V` and Unicode digits raise
  `LvmError` (0.2 read `1_0` as 10). A period is also read as the decimal point in a file
  declaring a comma, as LabVIEW writes such files.
- A file header or segment header without `***End_of_Header***` raises `LvmError`.
- The writer refuses data it cannot write faithfully (`TypeError` or `ValueError`, see the
  guide) and writes nothing in that case: `bool` and `str` samples, names holding the
  separator or a line break, reserved or empty names, unknown separator or `X_Columns`
  names. Samples may be any iterable of real numbers (lists, NumPy arrays, generators,
  `Decimal`, `Fraction`).
- Separator and `X_Columns` names are accepted in any case and written as LabVIEW spells
  them (`separator="tab"` writes `Tab`).
- `read_lvm` and `write_lvm` take any path-like object.
- `Channel`, `Segment`, `LvmFile` and `LvmError` report the module `lvmio`.
- Error messages give the line number and quote at most 40 characters.
- The command line reads standard input as bytes, catches every reading error with one line
  on standard error, and exits quietly when its output pipe closes. Output to a file or a
  pipe is UTF-8. JSON output writes infinities as `"Inf"` and `"-Inf"`, CSV as `Inf` and
  `-Inf`.

### Fixed

- A file header repeated between segments (a later LabVIEW session appending) no longer
  produces an empty segment.
- `1e-9` was written as `0.000000` and lost.
- CSV output from `lvmio dump` had a blank line after every row on Windows.

## [0.2.1]

### Changed

- The `.lvm` test fixtures, whose origin was not recorded, are replaced by files generated
  by `scripts/make_lvm_fixtures.py` with the same layouts (tab and comma separators, decimal
  comma, empty X column, row comments, empty channels). The sdist is limited to the package,
  the tests, the fixture generator and the docs.

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

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
- `Segment.comment`, the comment of a data set; `Segment.notes`, its `Notes` line;
  `LvmFile.description`, the file's `Description` line; `Channel.date` and `Channel.time`,
  each channel's own start date and time. All are written back where LabVIEW puts them.
- `python -m lvmio`, and `--encoding` on every command.

### Changed

- Samples are written in LabVIEW's number format: fixed notation when the decimal exponent
  is from -4 to 6, exponent notation otherwise, exact ties rounded as LabVIEW rounds them
  (the guide notes where lvmio's last digit can differ),
  `NaN`, `Inf`, `-Inf`; `X0` keeps 17 significant digits.
- Comments are written and read with LabVIEW's escapes (`\XX` for control characters,
  `\\` for a backslash), so they may hold any character; a comment is one cell.
- A row whose cells are all empty is read as a row of NaN, as LabVIEW reads it; only a
  line without a separator ends a segment. A non-empty cell after the last column raises
  `LvmError` instead of being dropped.
- Rows with fewer cells than the column line, a data row after a blank line, a header
  block whose end marker does not come before a blank line, and a `Decimal_Separator`
  other than `.` or `,` (or a comma in a comma-separated file) raise `LvmError`.
- The writer refuses names and header fields starting or ending with any whitespace,
  unordered samples (sets, mappings), finite numbers too large for a double, and a comment
  on a segment with no samples.
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
- `precision` must be an `int` from 0 to 17 (0.2 took any number of decimals and floats),
  and X values and `Delta_X` keep at least 6 decimals whatever the precision.
- Mapping keys must be `str` (0.2 turned other keys into names), and `x0` and `delta_x`
  must be finite.
- A channel stops at its own `Samples` count when only empty cells follow, so a shorter
  channel reads back at its length (0.2 padded every channel with NaN to the longest one;
  LabVIEW's reader pads to the largest count). `Segment` and `LvmFile` store
  their containers as lists.
- X cells must be empty or numbers (0.2 ignored them); a blank `X0` or `Delta_X` cell means
  its default (0.2 raised `LvmError`); an empty `X_Dimension` cell stays empty.
- Rows after the first that carry a comment, or whose X value does not follow the previous
  one by the increment, start a new segment, as LabVIEW's "one header only" mode appends
  later writes; the segment keeps that row's comment, X origin and increment.
- `Channel` stores its `data` as a list, whatever iterable it is given.
- `--segment` takes an optional minus sign and digits only (0.2 accepted `+0`).
- The `dev` extra is gone: development tools are listed in `requirements-dev.txt`.
- `Channel`, `Segment`, `LvmFile` and `LvmError` report the module `lvmio`.
- Error messages give the line number and quote at most 40 characters.
- The command line reads standard input as bytes, catches every reading error with one line
  on standard error, and exits quietly when its output pipe closes. A malformed
  `--segment` value is refused, quoting at most 20 characters of it. `lvmio header` shows
  the description. Output to a file or a
  pipe is UTF-8. JSON output writes infinities as `"Inf"` and `"-Inf"`, CSV as `Inf` and
  `-Inf`.

### Fixed

- A file header repeated between segments (a later LabVIEW session appending) no longer
  produces an empty segment.
- `1e-9` was written as `0.000000` and lost.
- CSV output from `lvmio dump` had a blank line after every row on Windows.
- `lvmio dump --time` as CSV gave every channel the first channel's X axis; channels with
  their own `X0` or `Delta_X` now get their own `X_Value` column. `lvmio channels` escapes
  control characters in names and units.

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

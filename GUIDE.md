# lvmio guide

## The format as LabVIEW 2026 writes it

Everything below was observed in files written by LabVIEW 2026 (26.3.1f1) through the Write
To Measurement File express VI and its worker VI, on a Windows system with Spanish regional
settings (decimal comma). The files are in `tests/fixtures/labview2026` with a manifest.

A file starts with a header block: `LabVIEW Measurement`, then one `key<separator>value`
line each for `Writer_Version`, `Reader_Version`, `Separator`, `Decimal_Separator`,
`Multi_Headings`, `X_Columns`, `Time_Pref`, `Operator`, `Date` and `Time`, closed by
`***End_of_Header***` and a line holding only the separator. Lines end with CRLF.

Each data segment then has its own header: `Channels`, `Samples`, `Date`, `Time`,
`Y_Unit_Label` (only when a channel has a unit), `X_Dimension`, `X0` and `Delta_X`, closed by
`***End_of_Header***`, followed by a column line and the data rows, and a blank line.

| `X_Columns` | Column line | Data row |
| --- | --- | --- |
| `No` | `X_Value`, the channel names, `Comment` | an empty X cell, then one cell per channel |
| `One` | the same | the X value of the first channel, then one cell per channel |
| `Multi` | `X_Value` and a name for every channel, then `Comment` | an X cell before every channel's cell |

In the per-channel header lines each channel has one cell, plus one empty cell at the end;
in `Multi` files each channel's cell is followed by an empty one, so the cells line up with
the X column of each channel. The `Channels` line is padded with empty cells to the same
width. The comment of a data set goes in the Comment column of its first row.

Numbers: a sample is written with 6 decimals in fixed notation when it is zero or its
magnitude is from 1e-4 up to (not including) 1e7, and in exponent notation otherwise, with
6 decimals in the mantissa and an exponent without padding (`1,500000E-7`, `1,000000E+300`).
NaN is `NaN`, the infinities `Inf` and `-Inf`. `X0` has 16 decimals in exponent notation
(`0,0000000000000000E+0`). These rules match every one of 400 seeded values, from
subnormals to the largest double, that LabVIEW wrote in `numbers.lvm`.

When a second LabVIEW session appends to an existing file it writes the whole file header
again before its segment.

Text is written in the system code page (Windows-1252 here): a comment `café` is stored as
the byte `0xE9` for `é`.

## Writing

`format_lvm` returns the text; `write_lvm` encodes it (UTF-8 unless `encoding` is given)
and writes it. Both lay a file out as above, so a file read with lvmio and written back is
the same file. That holds for every capture except two: `period_decimal.lvm`, where LabVIEW
mixed periods into a file that declares a comma (lvmio writes the declared separator
throughout), and `appended_runs.lvm`, whose repeated file header lvmio does not repeat.

Samples may be given as any iterable of real numbers: a list, a tuple, a `range`, a NumPy
array or a generator. They are stored as Python floats.

`Multi_Headings` is written as `Yes` when `LvmFile.multi_headings` is true or the file has
more than one segment. `precision` sets the decimals of the samples, of the X values and of
`Delta_X` (6 by default, as LabVIEW). With `precision=17` every value in exponent notation
reads back exactly; values written in fixed notation keep 17 decimals.

The writer refuses, before writing anything:

| Error | When |
| --- | --- |
| `TypeError` | data that is not an `LvmFile`, `Segment`, list of `Channel` or mapping of `str` to an iterable of numbers; a sample, `x0` or `delta_x` that is not a real number (`int`, `float`, `Fraction`, `Decimal` and NumPy numbers are; `bool`, `str` and `complex` are not); a text field that is not `str`; `precision` that is not an `int` |
| `ValueError` | a separator other than Tab or Comma, a decimal separator other than `.` or `,`, a comma as both; `X_Columns` other than No, One or Multi; a name, unit, dimension or header field holding the separator or a line break, or starting or ending with blanks; an empty channel name or one called `X_Value` or `Comment`; an empty `x_dimension`; a comment with a line break; `precision` outside 0 to 17; a number too large for a double (`10**400`) or a signalling `Decimal` NaN; text the chosen encoding cannot hold (the message names the character) |
| `LookupError` | `write_lvm` with an unknown encoding name |

## Reading

`read_lvm(path)` reads the bytes as UTF-8 and, when they are not valid UTF-8, as
Windows-1252; `encoding=` fixes the encoding instead. `parse_lvm(text)` takes text.

- The column line decides the layout: an `X_Value` column is never a channel, and a last
  `Comment` column is the comment column. Header cells are matched to channels by column
  position, so `No`, `One` and `Multi` files give the same channels.
- An empty cell, or a row shorter than the column line, is a missing sample: NaN. Every
  channel of a segment has one value per data row, as in LabVIEW's reader.
- A number is an optional sign, digits with an optional decimal point, and an optional
  exponent, or `NaN`, `Inf` or `Infinity` in any case. Spaces and tabs around it are
  ignored. In a file declaring a decimal comma both the comma and the period are read as the
  decimal point.
- `X0` and `Delta_X` default to 0 and 1, `X_Dimension` to `Time`, a unit to empty.
- A repeated file header between segments is skipped.
- `Segment.comment` is the comment cell of the first data row.
- `LvmFile.multi_headings` is the file's `Multi_Headings` field.

### Where lvmio and LabVIEW's reader differ

LabVIEW's Read From Measurement File reads the longest number at the start of a cell and
ignores the rest. lvmio refuses such cells with an `LvmError` instead of returning part of
them:

| Cell | LabVIEW reads | lvmio |
| --- | --- | --- |
| `1_0` | 1 | refuses (Python's `float` would read 10) |
| `0x10` | 0 | refuses |
| `1,5` in a file declaring a period | 1 | refuses |
| `2.5V` | 2.5 | refuses |
| `2.500000` in a file declaring a comma | 2 | 2.5 |

The last row is what LabVIEW's writer produces when it is set to a period on a comma
locale (`period_decimal.lvm`): LabVIEW's reader then truncates its own values, while lvmio
reads the values that were written. Wherever both read a number, it is the same number; the
tests check every capture for this.

### Reading errors

`LvmError` (a `ValueError`) is raised for text that is not a LabVIEW Measurement file:

- the first line is not `LabVIEW Measurement`;
- the file header or a segment header has no `***End_of_Header***` line;
- a segment header is not followed by a column line;
- a cell is not a number as defined above (the message gives the line number);
- the bytes are not valid in the encoding (or in neither UTF-8 nor Windows-1252).

Messages quote at most 40 characters of the offending text. `read_lvm` raises `OSError`
for files it cannot open, `LookupError` for an unknown encoding name, and `parse_lvm` raises
`TypeError` for anything but `str`.

## Command line

| Command | Output |
| --- | --- |
| `lvmio header FILE [--json]` | the file header fields and the number of segments |
| `lvmio channels FILE` | per segment, each channel with its unit and sample count |
| `lvmio dump FILE [--channel NAME] [--segment N] [--format csv\|json] [--time]` | the samples; CSV leaves missing samples empty and writes infinities as `Inf` and `-Inf`; JSON writes missing samples as `null` and infinities as `"Inf"` and `"-Inf"` |

Every command takes `--encoding` and `-` for standard input. Output sent to a file or a pipe
is UTF-8. Exit status 0 on success; 1 on any reading error, with one line on standard
error; 2 for invalid arguments, with argparse's usage message.

## Objects

`Channel`, `Segment` and `LvmFile` are frozen dataclasses: their fields cannot be
reassigned, but the lists they hold (samples, channels, segments) are ordinary lists, so
the objects are not hashable. They compare by value.

## Upgrading from 0.2

- Numbers are written in LabVIEW's format. 0.2 wrote every sample with six fixed decimals,
  so `1e-9` became `0.000000` and `1e300` a 301-digit number; NaN was written as an empty
  cell and infinity as `inf`.
- The column line always starts with `X_Value`, as LabVIEW writes it, also with
  `X_Columns` `No`; the header lines are padded as LabVIEW pads them, `X0` keeps 17
  significant digits and `Y_Unit_Label` is left out when no channel has a unit.
- `X_Columns` `Multi` is read and written (0.2 read the extra X columns as channels).
- A repeated file header no longer turns into an empty segment.
- Cells such as `1_0`, `0x10` or Unicode digits raise `LvmError`; 0.2 read `1_0` as 10.
- `read_lvm` reads Windows-1252 files; 0.2 raised `UnicodeDecodeError`.
- A file or segment header without `***End_of_Header***` raises `LvmError`; 0.2 returned
  fewer segments.
- `LvmFile.multi_headings` is now a field read from the file (it was computed from the
  number of segments). `Segment` has a new `comment` field.
- New: `format_lvm`, the `x_columns` and `encoding` arguments, `encoding` for `read_lvm`,
  `python -m lvmio` and `--encoding` on the command line.
- The writer checks its input (see the table above) instead of writing a file that reads
  back differently. It now accepts any iterable of real numbers as samples (0.2 took
  sequences, and also `str` digits and `Decimal` through `float`): `str` and `bool` samples
  are refused.
- Separator and `X_Columns` names are accepted in any case and written as LabVIEW spells
  them (`separator="tab"` writes `Tab`).
- The command line no longer writes blank lines between CSV rows on Windows and writes
  valid JSON for infinities.

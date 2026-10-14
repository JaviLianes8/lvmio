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

Numbers: the notation follows `e = floor(log10(|x|))` computed in double precision. When
the value is zero or `e` is from -4 to 6 the sample is written in fixed notation with 6
decimals, rounding the exact binary value with ties toward zero (`0.0234375` is written
`0,023437`). Otherwise it is written in exponent notation with 6 decimals in the mantissa
and an exponent without padding (`1.5e-7` is `1,500000E-7`). An exact tie in exponent
notation goes away from zero (`10000005` is written `1,000001E+7`), except at the decimal
exponents 11, 16 and 17, where LabVIEW rounds it toward zero (`436280450000` is
`4,362804E+11`); exact ties exist only for exponents 7 to 19, and `exponent_ties.lvm` holds
twelve for each. Because `e` is computed in double, the largest double below 1e7 is written
`1,000000E+7` and the largest below 1e-4 is `0,000100`. NaN is `NaN`, the infinities `Inf`
and `-Inf`. `X0` has 16 decimals in exponent notation (`0,0000000000000000E+0`).

lvmio follows this rule. It matches every value LabVIEW wrote in `numbers.lvm` (400 seeded
values from subnormals to the largest double), `ties.lvm` (404 exact ties and boundary
neighbours) and `exponent_ties.lvm` (156 exact ties). It differs from LabVIEW by one unit
in the last written digit, in fixed or exponent notation, for doubles that lie within about
1e-17 (relative) of a halfway point without being one: LabVIEW does not round those from
their exact value, and no rule reproduced it. In `near_ties.lvm`, 400 doubles chosen to be
the nearest to halfway points, 20 are written one unit apart (`9.9999995e-239` is `9,999999E-239` from LabVIEW and
`1,000000E-238` from lvmio). Measured values are practically never that close to a halfway
point.

Comments: the comment of a data set goes in the Comment cell of its first row. LabVIEW
escapes a backslash as two backslashes and a character below 0x20 as a backslash and two
upper-case hexadecimal digits (a tab is `\09`, CR LF is `\0D\0A`); everything else,
DEL included, is written as it is. Its reader decodes the same codes.

X values: LabVIEW computes the X column from the waveform's true increment but writes
`Delta_X` in the sample number format (6 decimals, or a 6-decimal mantissa in exponent
notation such as `2,083333E-5`), so for an increment that does not fit (1/2048 s is
written `0,000488`) the X cells and `Delta_X` disagree in the file. lvmio, like LabVIEW's
own reader, takes the increment from `Delta_X`; it writes X cells as `x0 + i * delta_x`,
which can also differ from LabVIEW by one unit in the last decimal for X values within
about 1e-16 (relative) of a halfway point, with or without an `X0` offset (14 of 3000 rows
for an increment of 1e-7 in `delta_x_1e-7.lvm`). LabVIEW's reader starts the waveform at
the segment's `Date` and `Time` plus `X0`; `Channel.time_axis()` is relative to `X0` only,
and a file with an empty `Date` and `Time` reads in LabVIEW as starting in 1904.

When a second LabVIEW session appends to an existing file it writes the whole file header
again before its segment.

Text is written in the system code page (Windows-1252 here): a comment `café` is stored as
the byte `0xE9` for `é`.

## Writing

`format_lvm` returns the text; `write_lvm` encodes it (UTF-8 unless `encoding` is given)
and writes it. Both lay a file out as above, so a file read with lvmio and written back is
the same file. That holds for every capture except these: `period_decimal.lvm`, where
LabVIEW mixed periods into a file that declares a comma (lvmio writes the declared separator
throughout); `appended_runs.lvm`, whose repeated file header lvmio does not repeat;
`ties.lvm`, where LabVIEW wrote 9999999.9999995 as `10000000,000000`, which reads back as
1e7 and is then written `1,000000E+7`; and `near_ties.lvm`, where 9.99999996e-5 is written
`1,000000E-4`, reads back as 1e-4 and is then written `0,000100`; `delta_x_2048hz.lvm`,
whose increment does not fit the `Delta_X` format, so lvmio rewrites its X column from
`Delta_X`; and `delta_x_1e-7.lvm`, whose increment fits but where 14 X cells are near ties
(see X values above). The samples are unchanged in all of them. The same holds for
lvmio's own output of such values: rounding to seven digits can move a value across a
notation boundary, so a second write can spell it differently.
Comments are escaped as LabVIEW escapes them; in a comma-separated file a comma in a comment
is escaped too (`\2C`), so the comment stays one cell.

Samples may be given as any iterable of real numbers: a list, a tuple, a `range`, a NumPy
array or a generator. They are stored as Python floats.

`Multi_Headings` is written as `Yes` when `LvmFile.multi_headings` is true or the file has
more than one segment. `precision` sets the decimals of the samples, of the X values and of
`Delta_X` (6 by default, as LabVIEW; X values and `Delta_X` never get fewer than 6, so a
low precision cannot zero the X axis). With `precision=17` every value in exponent notation
reads back exactly; values written in fixed notation keep 17 decimals.

LabVIEW reads a file in the Windows code page. Text written in UTF-8 (the default) comes
back garbled in LabVIEW when it is not ASCII (`café` as `cafÃ©`); pass
`encoding="cp1252"` (or the code page of the LabVIEW machine) when the file is for LabVIEW.

The writer refuses, before writing anything:

| Error | When |
| --- | --- |
| `TypeError` | data that is not an `LvmFile`, `Segment`, list of `Channel` or mapping of `str` to an iterable of numbers; a sample, `x0` or `delta_x` that is not a real number (`int`, `float`, `Fraction`, `Decimal` and NumPy numbers are; `bool`, `str` and `complex` are not); a text field that is not `str`; `precision` that is not an `int` |
| `TypeError` (continued) | unordered samples (a `set` or a mapping) and `memoryview` samples, refused like `bytes` |
| `ValueError` | a separator other than Tab or Comma, a decimal separator other than `.` or `,`, a comma as both; `X_Columns` other than No, One or Multi; a name, unit, dimension or header field holding the separator or a line break, or starting or ending with any whitespace character (as Python's `str.strip` sees it, which is what the reader strips); an empty channel name or one called `X_Value` or `Comment`; an empty `x_dimension`; a comment on a segment with no samples (it has no row to go in), or a segment date or time on a segment with no channels (there is no cell for it); `precision` outside 0 to 17; a number too large for a double (`10**400`, `Decimal("1e400")`) or a signalling `Decimal` NaN; text the chosen encoding cannot hold (the message names the character) |
| `LookupError` | `write_lvm` with an unknown encoding name |

Text fields are copied to plain `str` and `precision` to a plain `int` before they are
checked, so a subclass cannot change what is checked or written. Exceptions raised by the
caller's own objects (a `__float__` or `__iter__` that fails) pass through unchanged.

## Reading

`read_lvm(path)` reads the bytes as UTF-8 and, when they are not valid UTF-8, as
Windows-1252; `encoding=` fixes the encoding instead. `parse_lvm(text)` takes text.

- The column line decides the layout: an `X_Value` column is never a channel, and a last
  `Comment` column is the comment column. Header cells are matched to channels by column
  position, so `No`, `One` and `Multi` files give the same channels.
- An empty cell is a missing sample: NaN. Every channel of a segment has one value per data
  row, as in LabVIEW's reader. A row with fewer cells than the last channel's column is
  refused, as LabVIEW refuses it.
- A number is an optional sign, digits with an optional decimal point, and an optional
  exponent, or `NaN`, `Inf` or `Infinity` in any case. Spaces and tabs around it are
  ignored. In a file declaring a decimal comma both the comma and the period are read as the
  decimal point.
- `X0` and `Delta_X` default to 0 and 1, `X_Dimension` to `Time`, a unit to empty.
- A repeated file header between segments is skipped.
- `Segment.comment` is the comment cell of the first data row, with `\\` and `\XX`
  decoded; any other backslash is kept as written.
- `Decimal_Separator` must be `.` or `,`.
- `LvmFile.multi_headings` is the file's `Multi_Headings` field.

### Where lvmio and LabVIEW's reader differ

Every file in `tests/fixtures/labview2026` was also given to LabVIEW's Read From
Measurement File, and `read_results.json` holds what it returned. Wherever both read a
value it is the same value, apart from the cases in the last table below. The places where
only one of them reads a value:

LabVIEW reads the longest number at the start of a cell and ignores the rest; lvmio refuses
such cells with an `LvmError` instead of returning part of them:

| Input | LabVIEW reads | lvmio |
| --- | --- | --- |
| `1_0` | 1 | refuses (Python's `float` would read 10) |
| `0x10`, `0b1` | 0 | refuses |
| `1,5` in a file declaring a period, `1 2`, `1.#INF`, `1d5` | 1 | refuses |
| `2.5V`, `1.5e` | 2.5, 1.5 | refuses |
| `1E5.5`, `1e5e5` | 100000 | refuses |
| `Inf5`, `Infinite`, `infinityx` | Inf | refuses |
| `NaN1`, `nan(ind)` | NaN | refuses |
| a blank line between data rows | goes on reading rows | refuses: a blank line ends a segment |

LabVIEW refuses these (error 100) and lvmio reads them:

| Input | lvmio reads |
| --- | --- |
| `-nan`, `+NaN` | NaN |
| a cell holding only spaces | NaN, like an empty cell |
| a column line without `X_Value` (as lvmio 0.2 wrote `X_Columns` `No` files) | the columns as channels |
| a cell starting with a period in a file that declares a decimal comma (`+.5e+3`) | 500 |

Both read a value, but not the same one:

| Input | LabVIEW reads | lvmio |
| --- | --- | --- |
| `2.500000` in a file that declares a decimal comma | 2 | 2.5 |
| a comment holding `\zz` or ending with `\4` | NUL in place of the code, and drops the rest | the text as written |
| some cells, about one in a few thousand at 6 digits (`0.011227`, `-8.633024E-6`) | the double one unit in the last place away | the correctly rounded double, as Python's `float` |

The first row is what LabVIEW's writer produces when it is set to a period on a comma
locale (`period_decimal.lvm`): LabVIEW's reader then truncates its own values, while lvmio
reads the values that were written. LabVIEW's writer never produces the second. The third
is LabVIEW's own decimal conversion: `read/lvmio_ulp.lvm` holds six such cells, and
`0.011227` comes back from LabVIEW as 0.011227000000000001; no cell written with 17
digits was seen to differ.

LabVIEW's reader, driven through its ActiveX server, returned the first data set of a file on
every call, so only first data sets were compared with it; later segments are compared with
the values LabVIEW was given when it wrote them.

### Reading errors

`LvmError` (a `ValueError`) is raised for text that is not a LabVIEW Measurement file:

- the first line is not `LabVIEW Measurement`;
- the file header, a repeated file header or a segment header has no
  `***End_of_Header***` line before a blank line or the end of the text;
- a segment header is not followed by a column line;
- a data row follows a blank line, or a row has fewer cells than the column line needs;
- `Decimal_Separator` is not `.` or `,`, or is a comma in a comma-separated file;
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
is UTF-8; with no standard output at all the command prints nothing. Exit status 0 on success; 1 on any reading error, with one line on standard
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
- Rows shorter than the column line raise `LvmError`; 0.2 padded them with NaN.
- Comments are decoded and written with LabVIEW's escapes, and a comment is one cell.
- Samples are written with LabVIEW's rounding of exact ties.
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

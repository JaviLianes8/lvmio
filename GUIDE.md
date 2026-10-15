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
own reader, takes the increment from `Delta_X` (for a later write, see Reading); it writes X cells as `x0 + i * delta_x`,
which can also differ from LabVIEW by one unit in the last decimal for X values within
about 1e-16 (relative) of a halfway point, with or without an `X0` offset (14 of 3000 rows
for an increment of 1e-7 in `delta_x_1e-7.lvm`). `X0` itself is written with 17
significant digits, and for a value within a hair of a 17-digit halfway point LabVIEW's
last digit can differ from the correctly rounded one lvmio writes (2 of the 60 `X0`
values in `x0_offsets.lvm`); both spellings read back as the same double. lvmio does not
combine a segment's `Date` and `Time` with `X0`: `Channel.time_axis()` is relative to `X0`
only.

When a second LabVIEW session appends to an existing file it writes the whole file header
again before its segment.

Other header content LabVIEW writes: a file description (the File Description option) as a
`Description` line after `Operator`, escaped like a comment; a `Notes` line before
`Channels` when the channels' X values differ; and a `Date` and `Time` cell for each
channel, which can differ between channels. With "one header only" LabVIEW writes
`Multi_Headings No` and a single segment header, and later writes append bare rows to that
segment without updating its `Samples` count (`one_header_*.lvm`); a later write with
another number of channels gives rows of another width. With "no headers" it writes bare
rows, which neither reader takes for a measurement file.

Text is written in the system code page (Windows-1252 here): a comment `café` is stored as
the byte `0xE9` for `é`.

## Writing

`format_lvm` returns the text; `write_lvm` encodes it (UTF-8 unless `encoding` is given)
and writes it. Both lay a file out as above, so a file read with lvmio and written back is
the same file. That holds for every capture except these, where the samples read the same
but the text written back differs:

- `period_decimal.lvm`: LabVIEW mixed periods into a file that declares a comma; lvmio
  writes the declared separator throughout.
- `appended_runs.lvm`: lvmio does not repeat the repeated file header.
- `ties.lvm` and `near_ties.lvm`: 9999999.9999995 is written `10000000,000000` and reads
  back as 1e7, then written `1,000000E+7`; 9.99999996e-5 is written `1,000000E-4`, then
  `0,000100`. Rounding to seven digits can move a value across a notation boundary, in
  lvmio's own output too.
- `delta_x_2048hz.lvm`, `delta_x_1e-7.lvm` and `x0_offsets.lvm`: X cells are rebuilt from
  `Delta_X` (see X values above), and two `X0` values are spelled one unit apart.
- `one_header_same.lvm`, `one_header_gap.lvm`, `one_header_step.lvm` and the other
  `one_header_*.lvm` files: written back as separate segments with their own headers (see
  Reading).

lvmio's own files follow the same rules: an increment that does not fit the digits of
`Delta_X` (1/2048 at precision 6) is written with X cells from the exact increment, and a
read and a second write rebuild them from the rounded `Delta_X`; from then on the file is
stable.

`one_header_fewer.lvm` and `one_header_more.lvm` are refused (see the differences).
Comments are escaped as LabVIEW escapes them; in a comma-separated file a comma in a comment
is escaped too (`\2C`), so the comment stays one cell.

Samples may be given as any iterable of real numbers: a list, a tuple, a `range`, a NumPy
array or a generator. `Channel` turns its `data` into a list when it is created (its type is
`list[float]`), and the writer stores every sample as a Python float. A channel shorter
than the others is padded with empty cells, and its `Samples` count stays its own length.
lvmio reads it back at that length (it drops the empty cells past `Samples`); LabVIEW's
reader reads every channel up to the largest `Samples` count of the segment, so the padding
comes back as NaN there. `Date` and `Time` are
written as given; LabVIEW expects its own form (`2026/10/14`, `10:00:00,5` with the file's
decimal separator) and reads other text differently.

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
| `ValueError` | a separator other than Tab or Comma, a decimal separator other than `.` or `,`, a comma as both; `X_Columns` other than No, One or Multi; a name, unit, dimension or header field holding the separator or a line break, or starting or ending with any whitespace character (as Python's `str.strip` sees it, which is what the reader strips); an empty channel name or one called `X_Value` or `Comment`; an `x0` or `delta_x` that is not finite; a `description` starting or ending with whitespace; a comment on a segment with no samples (it has no row to go in), or a segment date or time on a segment with no channels (there is no cell for it); `precision` outside 0 to 17; a number too large for a double (`10**400`, `Decimal("1e400")`) or a signalling `Decimal` NaN; text the chosen encoding cannot hold (the message names the character) |
| `LookupError` | `write_lvm` with an unknown encoding name |

Text fields are copied to plain `str` and `precision` to a plain `int` before they are
checked, so a subclass cannot change what is checked or written. Exceptions raised by the
caller's own objects pass through unchanged (a failing `__iter__`, or a `__float__` raising
anything but `ValueError` or `ArithmeticError`, which are reported as "cannot be held in a
double").

## Reading

`read_lvm(path)` reads the bytes as UTF-8 and, when they are not valid UTF-8, as
Windows-1252; `encoding=` fixes the encoding instead. `parse_lvm(text)` takes text.

- The column line decides the layout: an `X_Value` column is never a channel, and a last
  `Comment` column is the comment column. Header cells are matched to channels by column
  position, so `No`, `One` and `Multi` files give the same channels.
- An empty cell is a missing sample: NaN, and a line of separators is a row of NaN (also
  one placed between two segments, which adds a row to the segment before it); only a blank
  line, without a separator and with nothing but spaces, ends a segment. An X cell must be
  empty or a number, so a stray header line between data rows is refused. A channel has one
  value per data row, except that it stops at its own `Samples` count when only empty
  cells follow (the padding of a shorter channel). Otherwise the `Samples` and `Channels`
  counts are not used: the column line and the data rows decide (LabVIEW's reader reads
  every channel up to the largest `Samples` count of the segment; see the differences
  below). A row with fewer cells than the last channel's column is refused, as
  LabVIEW refuses it.
- A number is an optional sign, digits with an optional decimal point, and an optional
  exponent, or `NaN`, `Inf` or `Infinity` in any case. Spaces and tabs around it are
  ignored. In a file declaring a decimal comma both the comma and the period are read as the
  decimal point.
- `X0` and `Delta_X` default to 0 and 1 when their line is missing, `X_Dimension` to
  `Time` when its line is missing (an empty cell stays empty), a unit to empty.
- A row after the first starts a new segment when it carries a comment, or when its X cell
  is not the previous X cell plus the increment, beyond half a unit of the `Delta_X` cell's
  last digit plus a unit of each X cell's last digit: the X restarts, jumps or changes step.
  The new segment has the same channels, the comment of that row, an `X0` from that row's X
  cell and, when its own X cells step differently and the next step agrees, that increment
  (rounded to the digits the cells are printed with). This is how LabVIEW's "one header
  only" mode appends each later write (`one_header_*.lvm`, including a step change of 25 %
  and a logging loop of one row per write), and how files with a comment on every write read
  without losing a comment or an X origin. A later write whose first row happens to continue
  the previous X stays one row longer in the earlier segment (every sample keeps its X
  value). In `X_Columns` `One` the shared X column gives the origin and increment of every
  channel of a later write; in `No`, where there are no X cells, only comments start a
  segment and its `X0` is extrapolated as `X0 + row * Delta_X`. A negative increment is an
  ordinary step (`negative_dx.lvm`).
- `Channel.date` and `Channel.time` are each channel's own `Date` and `Time` cells;
  `Segment.date` and `Segment.time` are the first channel's. `Segment.notes` is the
  `Notes` line and `LvmFile.description` the `Description` line, decoded like a comment.
  The writer writes them back where LabVIEW puts them.
- A non-empty cell after the last column of the column line (after the Comment column when
  there is one) is refused, so no data is dropped silently.
- A repeated file header between segments is skipped.
- `Segment.comment` is the comment cell of the first data row, with `\\` and `\XX`
  decoded; any other backslash is kept as written.
- `Decimal_Separator` must be `.` or `,`.
- `LvmFile.multi_headings` is the file's `Multi_Headings` field.

### Where lvmio and LabVIEW's reader differ

Every file in `tests/fixtures/labview2026` was also given to LabVIEW's Read From
Measurement File, and `read_results.json` holds what it returned. Wherever both read a
value it is the same value, apart from the cases in the last table below. The tables list
every difference found. Files written by LabVIEW's writer or by lvmio stay clear of most
of them; text that neither writer produces (hand-edited or from other programs) can meet
further differences in how the two readers treat malformed lines. The places where only
one of them reads a value:

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
| a form feed before or after the number (`\x0c1`, `\x0c1\x0c`) | 1 | refuses |
| a blank line between data rows | goes on reading rows | refuses: a blank line ends a segment |
| cells after the Comment column (`com`, `99`, `100`), or rows from a later "one header only" write with more or fewer channels (`one_header_more.lvm`, `one_header_fewer.lvm`) | the first comment cell, or the rows of the first write | refuses the file |
| a sign followed by spaces (`- 1`, `+ 2`, `- Inf`, `1e+ 5`) | -1, 2, -Inf, 100000 | refuses |
| a blank or spaces-only line inside the file header or a segment header, or before the column line | skips it | refuses: a header must reach its end marker before a blank line |
| a `Delta_X` cell that is blank or not a number | an increment of 0 (blank: lvmio uses 1) | refuses text; 1 for a blank cell |

LabVIEW refuses these (error 100) and lvmio reads them:

| Input | lvmio reads |
| --- | --- |
| `-nan`, `+NaN` | NaN |
| a cell holding only spaces or tabs | NaN, like an empty cell |
| a segment header without a `Samples` line | every data row |
| a `Channels` count above the number of channel columns | the channel columns |
| a segment header without a `Date` or a `Time` line | every data row |
| a segment header without an `X0` or a `Delta_X` line | defaults of 0 and 1 |
| a key with a space before or after it (`X0 `) | the key without the spaces |
| a UTF-8 byte order mark at the start of the file | the file |
| a column line without `X_Value` (as lvmio 0.2 wrote `X_Columns` `No` files) | the columns as channels |
| a cell starting with a period in a file that declares a decimal comma (`+.5e+3`) | 500 |

Both read a value, but not the same one:

| Input | LabVIEW reads | lvmio |
| --- | --- | --- |
| `2.500000` in a file that declares a decimal comma | 2 | 2.5 |
| a comment holding `\zz` or ending with `\4` | NUL in place of the code, and drops the rest | the text as written |
| some cells, about one in a few thousand at precisions below 17 (`0.011227`, `-8.633024E-6`) | the double one unit in the last place away | the correctly rounded double, as Python's `float` |
| a `Samples` count above the data rows (5 for 2 rows), in any layout | the rows, then NaN and zeros up to the count | the rows |
| a "one header only" file with later writes appended (`one_header_same.lvm`) | the rows of the first write (the `Samples` count) | every write, each as a segment |
| an `X_Dimension` other than `Time` or `Frequency` (`Other`) | an empty dimension (`relay/lvmio_dimensions.lvm`) | the text as written |
| an `X0` that is not a multiple of 2^-64 s, or at or beyond 2^63 s | the nearest LabVIEW timestamp (1.23e-9 as 1.2299999999640723e-9, 1e-20 as 0, 1e19 wraps negative; `relay/lvmio_x0.lvm`) | the number as written |
| a file without a `Y_Unit_Label` line | the unit `V` for every channel | an empty unit |
| a `Samples` count below the data rows (1 for 2 rows) | that many rows | every row |
| a blank `Samples` count (when no other channel has a count) | no samples | every row |
| a channel shorter than the others, its cells empty past its own `Samples` count | NaN up to the largest count of the segment | the channel at its own count |
| `Samples` counts that differ while every cell holds a value (`2` and `3` over 5 rows) | every channel to the largest count (3 rows) | every row |
| a `Channels ` key with a trailing space | no channels | every channel |
| a row of empty cells between data rows | NaN, then zeros for the rows after it | NaN for that row, then the rows as written |
| units with an empty cell before others (`""`, `A`, `V`) | the units shifted left past the empty cell (`A`, `V`, `""`) | each unit on its own channel |

The first row is what LabVIEW's writer produces when it is set to a period on a comma
locale (`period_decimal.lvm`): LabVIEW's reader then truncates its own values, while lvmio
reads the values that were written. LabVIEW's writer never produces the second. The third
is LabVIEW's own decimal conversion: `read/lvmio_ulp.lvm` holds six such cells, and
`0.011227` comes back from LabVIEW as 0.011227000000000001; no cell written with 17
digits was seen to differ. LabVIEW's writer writes a `Samples` count equal to the rows of
each channel except in its "one header only" mode, where the count covers only the first
write; the `Samples` rows matter for those files and for files from other writers
(`read/samples_*.lvm`). LabVIEW's reader takes a file without a `Y_Unit_Label` line, as
both writers leave it out when no channel has a unit, as having the unit `V`
(`relay/express_default.lvm`), and an empty `Date` and `Time`, lvmio's default, as
1904-01-01. The increments and units LabVIEW's reader takes are seen by having
it write back what it read (`relay/*.lvm`): a blank or text `Delta_X` comes back as
`0,000000`, and units after an empty unit cell move one channel to the left. LabVIEW's own
writer writes a unit cell for every channel once any channel has a unit, so its files are
not affected, and it may write a `Notes` line before `Channels`, which lvmio reads past.

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
for files it cannot open (and `ValueError` for a path holding a NUL character, as Python's
`open` does), `LookupError` for an unknown or invalid encoding name (`TypeError` when it is
not a `str`), and `parse_lvm` raises
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
  number of segments). New fields: `Segment.comment`, `Segment.notes`,
  `LvmFile.description`, `Channel.date` and `Channel.time`. `Channel` stores its `data` as
  a list.
- `precision` must be an `int` from 0 to 17 (0.2 took any number of decimals); X values
  and `Delta_X` keep at least 6 decimals whatever the precision.
- Mapping keys must be `str` (0.2 turned `1` into the channel name `'1'`).
- X cells must be empty or numbers (0.2 ignored them); a blank `X0` or `Delta_X` cell
  means the default (0.2 raised `LvmError`). Rows with a comment after the first row, or
  whose X value does not follow the previous one by the increment (it restarts, jumps or
  changes step), start a new segment.
- `--segment` takes only an optional minus sign and digits (0.2 took `+0`).
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

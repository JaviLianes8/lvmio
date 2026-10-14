# lvmio

Typed reader and writer for LabVIEW Measurement (`.lvm`) files, standard library only.

`.lvm` is the text format LabVIEW's Write To Measurement File express VI produces. lvmio
reads those files into frozen dataclasses and writes files in the same layout, byte for
byte: the files LabVIEW 2026 wrote in the test captures come back unchanged after a read
and a write (the guide explains the few exceptions), and LabVIEW's own reader reads
lvmio's files with the values that were written (to the last bit, except for about one
cell in a few thousand that LabVIEW's reader rounds one unit off).

## Install

```
pip install lvmio
```

Python 3.10 or newer. No runtime dependencies.

## Quick start

```pycon
>>> from lvmio import Channel, LvmFile, Segment, format_lvm, parse_lvm
>>> channels = [
...     Channel("Voltage", [1.0, 2.5, -3.25], unit="V", delta_x=0.1),
...     Channel("Current", [0.5, 0.25, 1e-9], unit="A", delta_x=0.1),
... ]
>>> text = format_lvm(LvmFile([Segment(channels, comment="run 1")]), operator="lab")
>>> lvm = parse_lvm(text)
>>> segment = lvm.segments[0]
>>> segment.names, segment["Current"].data, segment.comment
(['Voltage', 'Current'], [0.5, 0.25, 1e-09], 'run 1')
>>> segment["Voltage"].time_axis()
[0.0, 0.1, 0.2]

```

`write_lvm(path, data)` and `read_lvm(path)` do the same with files. `data` can be an
`LvmFile`, one `Segment`, a list of `Channel` objects or a mapping of name to samples
(any iterable of numbers, NumPy arrays included):

```pycon
>>> import pathlib, tempfile
>>> from lvmio import read_lvm, write_lvm
>>> path = pathlib.Path(tempfile.mkdtemp(), "quick.lvm")
>>> write_lvm(path, {"x": [1.0, 2.0], "y": [3.0, 4.0]}, decimal_separator=",")
>>> read_lvm(path).segments[0]["y"].data
[3.0, 4.0]

```

Keyword arguments set the file header: `operator`, `date`, `time`, `separator`
(`"Tab"` or `"Comma"`), `decimal_separator` (`"."` or `","`), `x_columns` (`"No"`, `"One"`
or `"Multi"`), `precision` (decimals per sample, 6 by default as in LabVIEW) and, for
`write_lvm`, `encoding`.

## What it handles

- The three X column layouts LabVIEW writes: `No` (an empty X column), `One` (one shared X
  column) and `Multi` (an X column before every channel).
- Tab and comma separators, the decimal comma, several segments with their comments, and a
  file header repeated in the middle of a file (LabVIEW writes one when a later session
  appends to the file).
- LabVIEW's number format, including how it rounds exact ties (`2.500000`,
  `1.000000E-9`, `NaN`, `Inf`, `-Inf`); empty cells read as NaN.
- Comments with LabVIEW's escapes (`\09` for a tab, `\\` for a backslash).
- Text in UTF-8 or in Windows-1252, the code page LabVIEW writes on a Western-European
  Windows system; `read_lvm` tries UTF-8 first and then Windows-1252. For a file LabVIEW
  will read, write with `encoding="cp1252"`: LabVIEW reads files in its code page.

Where LabVIEW reads part of a cell (`2.5V` as 2.5), lvmio refuses the cell; where both
read a value they agree, apart from cases the guide lists (LabVIEW's reader rounding a
few cells one unit in the last place off, and periods its own writer puts in a comma file).
The
[guide](https://github.com/JaviLianes8/lvmio/blob/main/GUIDE.md) lists every difference.

## Command line

```
lvmio header run.lvm                 # file header fields, --json for JSON
lvmio channels run.lvm               # channels and sample counts per segment
lvmio dump run.lvm --channel Voltage --time   # one channel as CSV with its X axis
lvmio dump run.lvm --format json     # a segment as JSON
lvmio header old.lvm --encoding cp1252
cat run.lvm | lvmio header -
```

`python -m lvmio` runs the same command. Reading errors print one line to standard error
and exit with status 1; invalid arguments exit with status 2.

## Why

LabVIEW reads and writes `.lvm` itself. On the Python side, the `lvm_read` package (1.26)
reads the format into NumPy arrays and has no writer. lvmio writes files in the layout
LabVIEW's own writer produces, so a Python program can hand data to a LabVIEW VI, and it
reads them back into typed objects without NumPy.

## Documentation

- [Guide](https://github.com/JaviLianes8/lvmio/blob/main/GUIDE.md): the format as LabVIEW
  2026 writes it, reading rules, errors, and upgrading from 0.2.
- [Changelog](https://github.com/JaviLianes8/lvmio/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvmio/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

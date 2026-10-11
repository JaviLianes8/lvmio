# lvmio

Typed reader and writer for the LabVIEW Measurement (.lvm) file format, stdlib only.

## Install

```
pip install lvmio
```

## Usage

Write channels to a spec-faithful `.lvm` file and read them back:

```python
from lvmio import Channel, LvmFile, Segment, read_lvm, write_lvm

channels = [
    Channel("Voltage", [1.0, 2.0, 3.0], unit="V", delta_x=0.1),
    Channel("Current", [0.5, 0.25, 0.125], unit="A", delta_x=0.1),
]
write_lvm("run.lvm", LvmFile(segments=[Segment(channels)]), operator="lab")

lvm = read_lvm("run.lvm")
first = lvm.segments[0].channels[0]
print(first.name, first.data)  # Voltage [1.0, 2.0, 3.0]
```

`write_lvm` also accepts a bare list of `Channel` objects, a single `Segment`,
or a mapping of name to samples:

```python
write_lvm("quick.lvm", {"x": [1.0, 2.0], "y": [3.0, 4.0]})
```

Keyword arguments override file header fields: `operator`, `date`, `time`,
`separator` (`"Tab"` or `"Comma"`), `decimal_separator`, and `precision` (the
number of decimal places used for numeric output).

### Working with a parsed file

The parsed objects are frozen dataclasses with convenient access:

```python
lvm = read_lvm("run.lvm")
segment = lvm.segments[0]

for channel in segment:  # Segment iterates over its channels
    print(channel.name, len(channel))

voltage = segment["Voltage"]  # access a channel by name
axis = voltage.time_axis()  # [x0, x0 + delta_x, ...], one value per sample
missing = segment.get("absent")  # None when the channel is not present
```

Empty cells in the data (unconnected channels, or rows without a value) parse to
`float('nan')`, so every channel keeps one value per row and stays aligned with its
own time axis.

`parse_lvm(text)` parses a `.lvm` string already in memory; `read_lvm(path)` is the
path based convenience that calls it.

## Command line

Installing the package adds an `lvmio` console command:

```
lvmio header run.lvm            # file metadata, add --json for JSON
lvmio channels run.lvm          # list the channels per segment
lvmio dump run.lvm --channel Voltage --time    # one channel as CSV with its time axis
lvmio dump run.lvm --format json               # all channels of a segment as JSON
cat run.lvm | lvmio header -    # read from standard input
```

Errors go to standard error and the process exits with status 1. Run `lvmio --help`
or `lvmio <command> --help` for the full list of options.

## Supported subset

The format has a file header block (`LabVIEW Measurement`, `Writer_Version`,
`Separator`, `Decimal_Separator`, `Multi_Headings`, `X_Columns`, `Time_Pref`,
`Operator`, `Date`, `Time`) followed by one or more data segments, each with its
own channel header and tab-delimited rows.

Covered:

- Tab and comma separators, and a configurable decimal separator (including the
  decimal comma and scientific notation that European LabVIEW writes).
- Single or multiple segments (`Multi_Headings` is set from the segment count).
- `X_Columns` set to `One` (a shared X axis from `X0` and `Delta_X`) or `No`. Real
  `No` files still carry an empty leading X column, and the reader handles that.
- Per-channel `Y_Unit_Label`, `X_Dimension`, `X0` and `Delta_X`.
- The trailing `Comment` column on the data header, and comments on some rows.
- Empty data cells, which become `float('nan')`.

Behaviour on genuine LabVIEW output is locked in by golden fixtures under
`tests/fixtures/` and cross-checked against the independent `lvm_read` package.

Out of scope for now: `X_Columns` set to `Multi` (one X column per channel) and
absolute-time X axes. These parse as plain columns but are not modelled.

## Why

LabVIEW produces and consumes `.lvm` natively with its Write/Read To Measurement File
express VIs, and on the Python side `lvm-read` already reads the format well. Reading,
then, is a solved problem. What is missing is the writer: there is no maintained,
typed Python package that **writes** a `.lvm` file a LabVIEW VI will read back, which
otherwise means matching NI's header blocks and tab-delimited segments by hand.
`lvmio` fills that writer gap and keeps a small, correct reader alongside it as a
convenience, not as the novelty, so a round trip stays within one dependency-free
package. It uses the standard library only.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

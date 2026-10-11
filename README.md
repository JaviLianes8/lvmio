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

## Supported subset

The format has a file header block (`LabVIEW Measurement`, `Writer_Version`,
`Separator`, `Decimal_Separator`, `Multi_Headings`, `X_Columns`, `Time_Pref`,
`Operator`, `Date`, `Time`) followed by one or more data segments, each with its
own channel header and tab-delimited rows.

Covered:

- Tab and comma separators, and a configurable decimal separator.
- Single or multiple segments (`Multi_Headings` is set from the segment count).
- `X_Columns` set to `One` (a shared X axis from `X0` and `Delta_X`) or `No`.
- Per-channel `Y_Unit_Label`, `X_Dimension`, `X0` and `Delta_X`.
- The trailing `Comment` column on the data header.

Out of scope for now: `X_Columns` set to `Multi` (one X column per channel) and
absolute-time X axes. These parse as plain columns but are not modelled.

## Why

`lvm-read` reads `.lvm` files well, but it is read-only: there is no maintained,
typed Python package that **writes** a `.lvm` file a LabVIEW VI will read back.
`lvmio` fills that writer gap and keeps a small, correct reader alongside it, so
a round trip stays within one dependency-free package. It uses the standard
library only.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

"""Serialise typed objects to spec-faithful LabVIEW Measurement (.lvm) text."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ._model import Channel, LvmFile, Segment

_END = "***End_of_Header***"
_EOL = "\r\n"


def write_lvm(
    path: str | Path,
    data: LvmFile | Segment | Sequence[Channel] | Mapping[str, Sequence[float]],
    *,
    operator: str | None = None,
    date: str | None = None,
    time: str | None = None,
    decimal_separator: str | None = None,
    separator: str | None = None,
    precision: int = 6,
) -> None:
    """Write ``data`` to ``path`` as a LabVIEW Measurement file.

    ``data`` may be a full ``LvmFile``, a single ``Segment``, a sequence of
    ``Channel`` objects, or a mapping of channel name to samples. Keyword
    arguments override the matching file header fields.
    """
    lvm = _as_file(data)
    if operator is not None:
        lvm.operator = operator
    if date is not None:
        lvm.date = date
    if time is not None:
        lvm.time = time
    if decimal_separator is not None:
        lvm.decimal_separator = decimal_separator
    if separator is not None:
        lvm.separator = separator
    text = _EOL.join(_render(lvm, precision)) + _EOL
    Path(path).write_text(text, encoding="utf-8", newline="")


def _as_file(data: object) -> LvmFile:
    if isinstance(data, LvmFile):
        return data
    if isinstance(data, Segment):
        return LvmFile(segments=[data])
    if isinstance(data, Mapping):
        channels = [Channel(str(k), [float(v) for v in vals]) for k, vals in data.items()]
        return LvmFile(segments=[Segment(channels)])
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        items = list(data)
        if not all(isinstance(c, Channel) for c in items):
            raise TypeError("sequence must contain Channel objects")
        return LvmFile(segments=[Segment(items)])
    raise TypeError("unsupported data type for write_lvm")


def _render(lvm: LvmFile, precision: int) -> list[str]:
    delim = _delimiter(lvm.separator)
    lines = _file_header(lvm, delim)
    for seg in lvm.segments:
        lines.append("")
        lines.extend(_segment(seg, lvm, delim, precision))
    return lines


def _delimiter(separator: str) -> str:
    return "," if separator.strip().lower() == "comma" else "\t"


def _file_header(lvm: LvmFile, delim: str) -> list[str]:
    return [
        "LabVIEW Measurement" + delim,
        f"Writer_Version{delim}{lvm.writer_version}",
        f"Reader_Version{delim}{lvm.reader_version}",
        f"Separator{delim}{lvm.separator}",
        f"Decimal_Separator{delim}{lvm.decimal_separator}",
        f"Multi_Headings{delim}{'Yes' if lvm.multi_headings else 'No'}",
        f"X_Columns{delim}{lvm.x_columns}",
        f"Time_Pref{delim}{lvm.time_pref}",
        f"Operator{delim}{lvm.operator}",
        f"Date{delim}{lvm.date}",
        f"Time{delim}{lvm.time}",
        _END + delim,
    ]


def _segment(seg: Segment, lvm: LvmFile, delim: str, precision: int) -> list[str]:
    chans = seg.channels
    n = len(chans)
    has_x = lvm.x_columns.strip().lower() != "no"
    dec = lvm.decimal_separator

    def row(label: str, values: list[str]) -> str:
        return delim.join([label, *values])

    lines = [
        f"Channels{delim}{n}",
        row("Samples", [str(len(c.data)) for c in chans]),
        row("Date", [seg.date] * n),
        row("Time", [seg.time] * n),
        row("Y_Unit_Label", [c.unit for c in chans]),
        row("X_Dimension", [c.x_dimension for c in chans]),
        row("X0", [_num(c.x0, precision, dec) for c in chans]),
        row("Delta_X", [_num(c.delta_x, precision, dec) for c in chans]),
        _END + delim,
    ]
    columns = (["X_Value"] if has_x else []) + [c.name for c in chans] + ["Comment"]
    lines.append(delim.join(columns))

    count = max((len(c.data) for c in chans), default=0)
    x0 = chans[0].x0 if chans else 0.0
    dx = chans[0].delta_x if chans else 1.0
    for i in range(count):
        fields = [_num(x0 + i * dx, precision, dec)] if has_x else []
        fields += [_num(c.data[i], precision, dec) if i < len(c.data) else "" for c in chans]
        lines.append(delim.join(fields))
    return lines


def _num(value: float, precision: int, decimal: str) -> str:
    text = f"{value:.{precision}f}"
    return text.replace(".", decimal) if decimal != "." else text

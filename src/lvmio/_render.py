"""Lay out a validated LvmFile line by line, as LabVIEW's writer does."""

from __future__ import annotations

from ._model import Channel, LvmFile, Segment
from ._number import format_number, format_x0

END = "***End_of_Header***"


def render(lvm: LvmFile, precision: int) -> list[str]:
    """The file's lines; the caller joins them with CRLF and ends with one."""
    delim = "," if lvm.separator == "Comma" else "\t"
    multi = "Yes" if lvm.multi_headings or len(lvm.segments) > 1 else "No"
    lines = [
        "LabVIEW Measurement" + delim,
        f"Writer_Version{delim}{lvm.writer_version}",
        f"Reader_Version{delim}{lvm.reader_version}",
        f"Separator{delim}{lvm.separator}",
        f"Decimal_Separator{delim}{lvm.decimal_separator}",
        f"Multi_Headings{delim}{multi}",
        f"X_Columns{delim}{lvm.x_columns}",
        f"Time_Pref{delim}{lvm.time_pref}",
        f"Operator{delim}{lvm.operator}",
        f"Date{delim}{lvm.date}",
        f"Time{delim}{lvm.time}",
        END + delim,
        delim,
    ]
    for segment in lvm.segments:
        lines.extend(_segment(segment, lvm, delim, precision))
        lines.append("")
    return lines


def _segment(seg: Segment, lvm: LvmFile, delim: str, precision: int) -> list[str]:
    chans, dec = seg.channels, lvm.decimal_separator
    multi = lvm.x_columns == "Multi"
    width = 2 * len(chans) if multi else len(chans) + 1

    def row(label: str, values: list[str]) -> str:
        cells = []
        for value in values:
            cells += [value, ""] if multi else [value]
        cells += [""] * (width - len(cells))
        return delim.join([label, *cells])

    lines = [
        delim.join(["Channels", str(len(chans)), *[""] * (width - 1)]),
        row("Samples", [str(len(c.data)) for c in chans]),
        row("Date", [seg.date] * len(chans)),
        row("Time", [seg.time] * len(chans)),
    ]
    if any(c.unit for c in chans):
        lines.append(row("Y_Unit_Label", [c.unit for c in chans]))
    lines += [
        row("X_Dimension", [c.x_dimension for c in chans]),
        row("X0", [format_x0(c.x0, dec) for c in chans]),
        row("Delta_X", [format_number(c.delta_x, precision, dec) for c in chans]),
        delim.join([END, *[""] * width]),
    ]
    names: list[str] = []
    for channel in chans:
        names += ["X_Value", channel.name] if multi else [channel.name]
    lines.append(delim.join((names if multi else ["X_Value", *names]) + ["Comment"]))
    count = max((len(c.data) for c in chans), default=0)
    for i in range(count):
        cells = [] if multi else [_x(chans[0], i, lvm, precision)]
        for channel in chans:
            sample = format_number(channel.data[i], precision, dec) if i < len(channel.data) else ""
            cells += [_x(channel, i, lvm, precision), sample] if multi else [sample]
        if i == 0 and seg.comment:
            cells.append(seg.comment)
        lines.append(delim.join(cells))
    return lines


def _x(channel: Channel, index: int, lvm: LvmFile, precision: int) -> str:
    """One X cell: empty for ``No`` and past the end of a channel's samples."""
    if lvm.x_columns == "No" or index >= len(channel.data):
        return ""
    value = channel.x0 + index * channel.delta_x
    return format_number(value, precision, lvm.decimal_separator)

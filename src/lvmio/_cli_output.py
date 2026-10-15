"""What the lvmio command prints: header fields, channel lists and data dumps."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math

from ._comment import escape_comment
from ._model import Channel, LvmFile, Segment


def dispatch(args: argparse.Namespace, lvm: LvmFile) -> int:
    """Run one subcommand on a parsed file and return the exit status."""
    if args.command == "header":
        _print_header(lvm, bool(args.json))
    elif args.command == "channels":
        _print_channels(lvm)
    elif args.command == "dump":
        _print_dump(lvm, args)
    return 0


def _header_fields(lvm: LvmFile) -> dict[str, object]:
    return {
        "writer_version": lvm.writer_version,
        "reader_version": lvm.reader_version,
        "separator": lvm.separator,
        "decimal_separator": lvm.decimal_separator,
        "x_columns": lvm.x_columns,
        "multi_headings": lvm.multi_headings,
        "time_pref": lvm.time_pref,
        "operator": lvm.operator,
        "date": lvm.date,
        "time": lvm.time,
        "description": lvm.description,
        "segments": len(lvm),
    }


def _print_header(lvm: LvmFile, as_json: bool) -> None:
    fields = _header_fields(lvm)
    if as_json:
        print(json.dumps(fields, indent=2, allow_nan=False))
        return
    for key, value in fields.items():
        text = escape_comment(value, "\t") if isinstance(value, str) else value
        print(f"{key}: {text}")


def _print_channels(lvm: LvmFile) -> None:
    for index, segment in enumerate(lvm):
        print(
            f"segment {index}: {len(segment)} channels, {max(segment.samples, default=0)} samples"
        )
        for channel in segment:
            unit = f" [{_shown(channel.unit)}]" if channel.unit else ""
            print(f"  {_shown(channel.name)}{unit}: {len(channel)} samples")


def _shown(text: str) -> str:
    """A name or unit with control characters escaped, so a file cannot drive the terminal."""
    return escape_comment(text, "	")


def _print_dump(lvm: LvmFile, args: argparse.Namespace) -> None:
    segment = _segment(lvm, int(args.segment))
    channels = _selected(segment, args.channel)
    if args.format == "json":
        _dump_json(channels, bool(args.time))
    else:
        _dump_csv(channels, bool(args.time))


def _segment(lvm: LvmFile, index: int) -> Segment:
    if not -len(lvm) <= index < len(lvm):
        raise IndexError(f"segment {index} out of range (file has {len(lvm)})")
    return lvm.segments[index]


def _selected(segment: Segment, name: str | None) -> list[Channel]:
    if name is None:
        return list(segment.channels)
    return [segment[name]]


def _at(data: list[float], index: int) -> float:
    return data[index] if index < len(data) else math.nan


def _dump_csv(channels: list[Channel], with_time: bool) -> None:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    count = max((len(c.data) for c in channels), default=0)
    axes = [c.time_axis() for c in channels] if with_time else []
    # One X column when every channel has the same X0 and Delta_X, otherwise one per channel.
    shared = with_time and len({(c.x0, c.delta_x) for c in channels}) <= 1
    own = with_time and not shared
    if shared and channels:
        axes[0] = max(channels, key=len).time_axis()
    header = (["X_Value"] if shared else []) + [
        cell for c in channels for cell in (["X_Value", c.name] if own else [c.name])
    ]
    writer.writerow(header)
    for i in range(count):
        row = [_fmt(_at(axes[0], i))] if shared else []
        for c, axis in zip(channels, axes if own else [[]] * len(channels), strict=True):
            row += ([_fmt(_at(axis, i))] if own else []) + [_fmt(_at(c.data, i))]
        writer.writerow(row)
    print(out.getvalue(), end="")


def _dump_json(channels: list[Channel], with_time: bool) -> None:
    payload = []
    for channel in channels:
        entry: dict[str, object] = {
            "name": channel.name,
            "unit": channel.unit,
            "data": [_jsonable(v) for v in channel.data],
        }
        if with_time:
            entry["time"] = [_jsonable(v) for v in channel.time_axis()]
        payload.append(entry)
    print(json.dumps(payload, indent=2, allow_nan=False))


def _fmt(value: float) -> str:
    """A CSV cell: empty for a missing sample, LabVIEW's spelling for infinities."""
    if math.isnan(value):
        return ""
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return repr(value)


def _jsonable(value: float) -> float | str | None:
    """JSON has no NaN or infinity: a missing sample is null, infinities are strings."""
    if math.isnan(value):
        return None
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return value

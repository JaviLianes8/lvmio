"""Command line interface for lvmio: inspect and export .lvm files."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections.abc import Sequence

from . import __version__
from ._errors import LvmError
from ._model import Channel, LvmFile, Segment
from ._read import parse_lvm, read_lvm

_EPILOG = """\
examples:
  lvmio header run.lvm
  lvmio header run.lvm --json
  lvmio channels run.lvm
  lvmio dump run.lvm --channel Voltage --time
  lvmio dump run.lvm --segment 0 --format json
  cat run.lvm | lvmio header -
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvmio`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        lvm = _load(args.path)
        return _dispatch(args, lvm)
    except (OSError, LvmError, KeyError, IndexError) as exc:
        print(f"lvmio: error: {_message(exc)}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvmio",
        description="Inspect and export LabVIEW Measurement (.lvm) files.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvmio {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    header = subparsers.add_parser("header", help="show the file header fields")
    header.add_argument("path", help="path to a .lvm file, or - for standard input")
    header.add_argument("--json", action="store_true", help="emit the header as JSON")

    channels = subparsers.add_parser("channels", help="list the channels per segment")
    channels.add_argument("path", help="path to a .lvm file, or - for standard input")

    dump = subparsers.add_parser("dump", help="dump data as CSV or JSON")
    dump.add_argument("path", help="path to a .lvm file, or - for standard input")
    dump.add_argument("--channel", help="dump only this channel (default: all)")
    dump.add_argument("--segment", type=int, default=0, help="segment index (default: 0)")
    dump.add_argument(
        "--format", choices=("csv", "json"), default="csv", help="output format (default: csv)"
    )
    dump.add_argument("--time", action="store_true", help="include the X (time) axis column")
    return parser


def _load(path: str) -> LvmFile:
    if path == "-":
        return parse_lvm(sys.stdin.read())
    return read_lvm(path)


def _dispatch(args: argparse.Namespace, lvm: LvmFile) -> int:
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
        "segments": len(lvm),
    }


def _print_header(lvm: LvmFile, as_json: bool) -> None:
    fields = _header_fields(lvm)
    if as_json:
        print(json.dumps(fields, indent=2))
        return
    for key, value in fields.items():
        print(f"{key}: {value}")


def _print_channels(lvm: LvmFile) -> None:
    for index, segment in enumerate(lvm):
        print(f"segment {index}: {len(segment)} channels, {len(_rows(segment))} samples")
        for channel in segment:
            unit = f" [{channel.unit}]" if channel.unit else ""
            print(f"  {channel.name}{unit}: {len(channel)} samples")


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


def _rows(segment: Segment) -> list[list[float]]:
    count = max((len(c.data) for c in segment.channels), default=0)
    return [[_at(c.data, i) for c in segment.channels] for i in range(count)]


def _at(data: list[float], index: int) -> float:
    return data[index] if index < len(data) else math.nan


def _dump_csv(channels: list[Channel], with_time: bool) -> None:
    out = io.StringIO()
    writer = csv.writer(out)
    header = (["X_Value"] if with_time else []) + [c.name for c in channels]
    writer.writerow(header)
    axis = channels[0].time_axis() if channels and with_time else []
    count = max((len(c.data) for c in channels), default=0)
    for i in range(count):
        time_cell = [_fmt(axis[i])] if with_time and i < len(axis) else ([""] if with_time else [])
        writer.writerow(time_cell + [_fmt(_at(c.data, i)) for c in channels])
    sys.stdout.write(out.getvalue())


def _dump_json(channels: list[Channel], with_time: bool) -> None:
    payload = []
    for channel in channels:
        entry: dict[str, object] = {
            "name": channel.name,
            "unit": channel.unit,
            "data": [_jsonable(v) for v in channel.data],
        }
        if with_time:
            entry["time"] = channel.time_axis()
        payload.append(entry)
    print(json.dumps(payload, indent=2))


def _fmt(value: float) -> str:
    return "" if math.isnan(value) else repr(value)


def _jsonable(value: float) -> float | None:
    return None if math.isnan(value) else value


def _message(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return f"no such channel: {exc.args[0]!r}"
    if isinstance(exc, FileNotFoundError):
        return f"no such file: {exc.filename}"
    return str(exc)


if __name__ == "__main__":
    raise SystemExit(main())

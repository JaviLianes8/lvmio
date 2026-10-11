"""Parse a LabVIEW Measurement (.lvm) file into typed objects."""

from __future__ import annotations

from pathlib import Path

from ._errors import LvmError
from ._model import Channel, LvmFile, Segment

_END = "***End_of_Header***"


def read_lvm(path: str | Path) -> LvmFile:
    """Read a LabVIEW Measurement file and return its typed representation."""
    raw = Path(path).read_text(encoding="utf-8")
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    delim = _detect_delimiter(lines)

    if not lines or _key(lines[0], delim) != "LabVIEW Measurement":
        raise LvmError("not a LabVIEW Measurement file")

    header, index = _collect_header(lines, 1, delim)
    decimal = header.get("Decimal_Separator", ".") or "."
    x_columns = header.get("X_Columns", "One") or "One"

    segments: list[Segment] = []
    while index < len(lines):
        index = _skip_blank(lines, index)
        if index >= len(lines):
            break
        fields, index = _collect_segment_fields(lines, index, delim)
        if index >= len(lines):
            break
        names = _channel_names([p.strip() for p in lines[index].split(delim)], x_columns)
        index += 1
        rows, index = _collect_rows(lines, index, delim)
        segments.append(_build_segment(names, rows, fields, x_columns, decimal))

    return LvmFile(
        segments=segments,
        writer_version=header.get("Writer_Version", "2"),
        reader_version=header.get("Reader_Version", "2"),
        separator=header.get("Separator", "Tab"),
        decimal_separator=decimal,
        x_columns=x_columns,
        time_pref=header.get("Time_Pref", "Relative"),
        operator=header.get("Operator", "unknown"),
        date=header.get("Date", ""),
        time=header.get("Time", ""),
    )


def _detect_delimiter(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("Separator"):
            return "," if "Comma" in line else "\t"
    return "\t"


def _key(line: str, delim: str) -> str:
    return line.split(delim)[0].strip()


def _collect_header(lines: list[str], index: int, delim: str) -> tuple[dict[str, str], int]:
    fields: dict[str, str] = {}
    while index < len(lines) and _key(lines[index], delim) != _END:
        parts = lines[index].split(delim)
        key = parts[0].strip()
        if key:
            fields[key] = parts[1].strip() if len(parts) > 1 else ""
        index += 1
    return fields, index + 1


def _collect_segment_fields(
    lines: list[str], index: int, delim: str
) -> tuple[dict[str, list[str]], int]:
    fields: dict[str, list[str]] = {}
    while index < len(lines) and _key(lines[index], delim) != _END:
        parts = lines[index].split(delim)
        key = parts[0].strip()
        if key:
            fields[key] = [p.strip() for p in parts[1:]]
        index += 1
    return fields, index + 1


def _collect_rows(lines: list[str], index: int, delim: str) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    while index < len(lines):
        line = lines[index]
        if line.strip() == "" or _key(line, delim) in ("Channels", "LabVIEW Measurement"):
            break
        rows.append(line.split(delim))
        index += 1
    return rows, index


def _channel_names(parts: list[str], x_columns: str) -> list[str]:
    start = 0 if x_columns.strip().lower() == "no" else 1
    names = list(parts[start:])
    while names and names[-1] == "":
        names.pop()
    if names and names[-1].lower() == "comment":
        names.pop()
    return names


def _build_segment(
    names: list[str],
    rows: list[list[str]],
    fields: dict[str, list[str]],
    x_columns: str,
    decimal: str,
) -> Segment:
    offset = 0 if x_columns.strip().lower() == "no" else 1
    units = fields.get("Y_Unit_Label", [])
    dims = fields.get("X_Dimension", [])
    x0s = fields.get("X0", [])
    deltas = fields.get("Delta_X", [])
    channels: list[Channel] = []
    for idx, name in enumerate(names):
        col = offset + idx
        data = [_to_float(r[col], decimal) for r in rows if col < len(r) and r[col].strip()]
        channels.append(
            Channel(
                name=name,
                data=data,
                unit=units[idx] if idx < len(units) else "",
                x0=_to_float(x0s[idx], decimal) if idx < len(x0s) else 0.0,
                delta_x=_to_float(deltas[idx], decimal) if idx < len(deltas) else 1.0,
                x_dimension=dims[idx] if idx < len(dims) else "Time",
            )
        )
    date = fields.get("Date", [""])
    time = fields.get("Time", [""])
    return Segment(channels, date[0] if date else "", time[0] if time else "")


def _skip_blank(lines: list[str], index: int) -> int:
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    return index


def _to_float(text: str, decimal: str) -> float:
    cleaned = text.strip().replace(decimal, ".") if decimal != "." else text.strip()
    try:
        return float(cleaned)
    except ValueError as exc:
        raise LvmError(f"not a number: {text!r}") from exc

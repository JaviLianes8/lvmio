"""Parse a LabVIEW Measurement (.lvm) file into typed objects."""

from __future__ import annotations

import os

from ._errors import LvmError
from ._model import LvmFile, Segment
from ._number import shorten
from ._segment import END, Lines, is_blank, parse_segment, skip_header

_MAGIC = "LabVIEW Measurement"


def read_lvm(path: str | os.PathLike[str], *, encoding: str | None = None) -> LvmFile:
    """Read a LabVIEW Measurement file and return its typed representation.

    With no ``encoding`` the file is read as UTF-8 and, when it is not valid UTF-8,
    as Windows-1252: LabVIEW on Windows writes text in the system code page. Raises
    ``LvmError`` for text that is not a measurement file (or not in the encoding),
    ``OSError`` when the file cannot be read and ``LookupError`` for an unknown encoding.

    >>> import lvmio, pathlib, tempfile
    >>> folder = tempfile.mkdtemp()
    >>> path = pathlib.Path(folder, "run.lvm")
    >>> lvmio.write_lvm(path, {"V": [1.0, 2.0]}, encoding="cp1252", operator="Jos\\xe9")
    >>> read_lvm(path).operator
    'José'
    """
    with open(os.fspath(path), "rb") as handle:
        data = handle.read()
    return parse_lvm(decode(data, encoding))


def decode(data: bytes, encoding: str | None) -> str:
    """Bytes to text: the given encoding, or UTF-8 and then Windows-1252."""
    if encoding is not None:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            raise LvmError(f"not {encoding} text at byte {exc.start}") from None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise LvmError(f"neither UTF-8 nor Windows-1252 text at byte {exc.start}") from None


def parse_lvm(text: str) -> LvmFile:
    """Parse LabVIEW Measurement text and return its typed representation.

    Raises ``LvmError`` for text that is not a measurement file and ``TypeError`` for
    anything but ``str``.

    >>> text = "LabVIEW Measurement\\t\\nX_Columns\\tNo\\n***End_of_Header***\\t\\n\\n"
    >>> text += "Channels\\t1\\n***End_of_Header***\\t\\nX_Value\\tV\\tComment\\n\\t1.5\\tok\\n"
    >>> lvm = parse_lvm(text)
    >>> lvm.x_columns, lvm.segments[0]["V"].data, lvm.segments[0].comment
    ('No', [1.5], 'ok')
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_lvm expects str, not {type(text).__name__}")
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[0].rstrip("\t, ") != _MAGIC:
        raise LvmError(f"not a LabVIEW Measurement file: line 1 is {shorten(lines[0])}")
    header, end, delim = _file_header(lines)
    decimal = header.get("Decimal_Separator") or "."
    cursor = Lines(lines, end + 1, delim)
    segments: list[Segment] = []
    while cursor.more():
        line = cursor.current()
        if is_blank(line, delim):
            cursor.advance()
        elif line.split(delim)[0].strip() == _MAGIC:
            skip_header(cursor)
        else:
            segments.append(parse_segment(cursor, decimal))
    return LvmFile(
        segments=segments,
        writer_version=header.get("Writer_Version", "2"),
        reader_version=header.get("Reader_Version", "2"),
        separator=header.get("Separator", "Tab"),
        decimal_separator=decimal,
        x_columns=header.get("X_Columns") or "One",
        time_pref=header.get("Time_Pref", "Relative"),
        operator=header.get("Operator", "unknown"),
        date=header.get("Date", ""),
        time=header.get("Time", ""),
        multi_headings=header.get("Multi_Headings", "").lower() == "yes",
    )


def _file_header(lines: list[str]) -> tuple[dict[str, str], int, str]:
    """The file header fields, the index of its end marker line and the delimiter."""
    end = next((i for i, line in enumerate(lines) if _key(line) == END), None)
    if end is None:
        raise LvmError(f"the file header has no {END} line")
    delim = "\t"
    for line in lines[1:end]:
        if _key(line) == "Separator" and line[len("Separator") + 1 :].strip().lower() == "comma":
            delim = ","
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        parts = line.split(delim)
        key = parts[0].strip()
        if key:
            fields[key] = parts[1].strip() if len(parts) > 1 else ""
    return fields, end, delim


def _key(line: str) -> str:
    """The first token of a line, whichever of tab or comma separates it."""
    return line.replace(",", "\t", 1).split("\t")[0].strip()

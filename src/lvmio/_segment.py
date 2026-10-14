"""Parse one data segment: its header block, column line and rows."""

from __future__ import annotations

import math
from collections.abc import Callable
from itertools import pairwise

from ._comment import unescape_comment
from ._errors import LvmError
from ._model import Channel, Segment
from ._number import parse_number
from ._split import own_step, starts

END = "***End_of_Header***"
_STOP = ("Channels", "LabVIEW Measurement")


class Lines:
    """A position in the file's lines, with the file's delimiter."""

    def __init__(self, lines: list[str], index: int, delim: str) -> None:
        self.lines, self.index, self.delim = lines, index, delim

    def more(self) -> bool:
        return self.index < len(self.lines)

    def current(self) -> str:
        return self.lines[self.index]

    def advance(self) -> None:
        self.index += 1

    def number(self) -> int:
        """The 1-based line number of the current line, for messages."""
        return self.index + 1


def is_blank(line: str, delim: str) -> bool:
    """Whether a line holds nothing but delimiters and spaces."""
    return not line.replace(delim, "").strip()


def first_token(line: str, delim: str) -> str:
    return line.split(delim, 1)[0].strip()


def skip_header(cursor: Lines) -> None:
    """Skip a repeated file header, which LabVIEW writes when it appends a run."""
    _to_end(cursor, "repeated file header", lambda line: None)
    cursor.advance()


def _to_end(cursor: Lines, what: str, take: Callable[[str], None]) -> None:
    """Hand every header line to ``take`` up to the end marker, which must come first."""
    start = cursor.number()
    while cursor.more() and first_token(cursor.current(), cursor.delim) != END:
        if is_blank(cursor.current(), cursor.delim):
            break
        take(cursor.current())
        cursor.advance()
    if not cursor.more() or first_token(cursor.current(), cursor.delim) != END:
        raise LvmError(f"line {start}: {what} has no {END} line")


def parse_segment(cursor: Lines, decimal: str) -> list[Segment]:
    fields: dict[str, list[str]] = {}
    where: dict[str, int] = {}

    def take(line: str) -> None:
        parts = line.split(cursor.delim)
        if parts[0].strip():
            fields[parts[0].strip()] = [p.strip() for p in parts[1:]]
            where[parts[0].strip()] = cursor.number()

    _to_end(cursor, "segment header", take)
    cursor.advance()
    if not cursor.more() or is_blank(cursor.current(), cursor.delim):
        raise LvmError(f"line {cursor.number()}: segment has no column line")
    columns = [p.strip() for p in cursor.current().split(cursor.delim)]
    cursor.advance()
    rows: list[list[str]] = []
    numbers: list[int] = []
    # A row whose cells are all empty is a row of missing samples, as LabVIEW reads it;
    # only a line without a separator ends the segment.
    while cursor.more() and (cursor.delim in cursor.current() or cursor.current().strip()):
        if first_token(cursor.current(), cursor.delim) in _STOP:
            break
        rows.append(cursor.current().split(cursor.delim))
        numbers.append(cursor.number())
        cursor.advance()
    return _build(columns, (fields, where), rows, numbers, decimal, cursor.delim)


def _layout(columns: list[str]) -> tuple[list[int], int | None]:
    """The column index of every channel, and of the Comment column if any."""
    last = len(columns)
    while last and columns[last - 1] == "":
        last -= 1
    comment = None
    if last and columns[last - 1].lower() == "comment":
        last -= 1
        comment = last
    channels = [i for i in range(last) if columns[i] != "X_Value"]
    return channels, comment


def _build(
    columns: list[str],
    header_block: tuple[dict[str, list[str]], dict[str, int]],
    rows: list[list[str]],
    numbers: list[int],
    decimal: str,
    delim: str,
) -> list[Segment]:
    fields, where = header_block
    positions, comment_at = _layout(columns)
    need = max(positions, default=-1) + 1
    limit = need if comment_at is None else comment_at + 1
    for row, number in zip(rows, numbers, strict=True):
        if len(row) < need:
            raise LvmError(f"line {number}: the row has {len(row)} cells, the column line {need}")
        if any(cell.strip() for cell in row[limit:]):
            raise LvmError(f"line {number}: a cell after the last column of the column line")
    shift = 1 if columns[0] == "X_Value" else 0

    def header(key: str, column: int) -> str | None:
        values = fields.get(key, [])
        cell = column - shift
        return values[cell] if 0 <= cell < len(values) and values[cell] != "" else None

    def dimension(column: int) -> str:
        """An empty X_Dimension cell stays empty; ``Time`` only when the line is missing."""
        if "X_Dimension" not in fields:
            return "Time"
        values, cell = fields["X_Dimension"], column - shift
        return values[cell] if 0 <= cell < len(values) else ""

    for column in (i for i, name in enumerate(columns[:need]) if name == "X_Value"):
        for row, number in zip(rows, numbers, strict=True):
            _cell(row, column, decimal, number)  # an X cell is empty or a number
    first = positions[0] if positions else shift
    x_column = 0 if shift else None
    segments = []
    step_text = header("Delta_X", first) if positions else None
    step = 1.0 if step_text is None else parse_number(step_text, decimal, where["Delta_X"])
    bounds = [*starts(rows, numbers, x_column, comment_at, decimal, step), len(rows)]
    for lo, hi in pairwise(bounds):
        channels: list[Channel] = []
        for column in positions:
            data = [
                _cell(r, column, decimal, n)
                for r, n in zip(rows[lo:hi], numbers[lo:hi], strict=True)
            ]
            x0_text, dx_text = header("X0", column), header("Delta_X", column)
            x0 = 0.0 if x0_text is None else parse_number(x0_text, decimal, where["X0"])
            dx = 1.0 if dx_text is None else parse_number(dx_text, decimal, where["Delta_X"])
            if lo:
                own = column - 1 if columns[column - 1] == "X_Value" and column > 1 else x_column
                cell = rows[lo][own].strip(" \t") if own is not None else ""
                x0 = parse_number(cell, decimal, numbers[lo]) if cell else x0 + lo * dx
                dx = own_step(rows[lo:hi], 0, own, decimal, numbers[lo:hi], dx)
            channels.append(
                Channel(
                    name=columns[column],
                    data=data,
                    unit=header("Y_Unit_Label", column) or "",
                    x0=x0,
                    delta_x=dx,
                    x_dimension=dimension(column),
                    date=header("Date", column) or "",
                    time=header("Time", column) or "",
                )
            )
        comment = ""
        if comment_at is not None and rows and len(rows[lo]) > comment_at:
            comment = unescape_comment(rows[lo][comment_at])
        notes = next((cell for cell in fields.get("Notes", []) if cell), "") if not lo else ""
        date, time = header("Date", first) or "", header("Time", first) or ""
        segments.append(Segment(channels, date=date, time=time, comment=comment, notes=notes))
    return segments


def _cell(row: list[str], column: int, decimal: str, line: int) -> float:
    """A data cell: empty or missing means a missing sample (NaN), as LabVIEW reads it."""
    text = row[column]
    if not text.strip(" \t"):
        return math.nan
    return parse_number(text, decimal, line)

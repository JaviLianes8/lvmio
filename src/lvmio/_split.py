"""Where a later write starts inside the rows of one segment header.

With "one header only" LabVIEW appends each later write to the rows of the first segment.
A later write shows as a row after the first that carries a comment, or whose X value goes
back; lvmio starts a new segment there so no comment or X origin is lost.
"""

from __future__ import annotations

from ._number import parse_number


def starts(
    rows: list[list[str]],
    numbers: list[int],
    x_column: int | None,
    comment_at: int | None,
    decimal: str,
) -> list[int]:
    """Row indexes that begin a segment, the first always 0."""
    found = [0]
    previous: float | None = None
    for index, row in enumerate(rows):
        x = _x(row, x_column, decimal, numbers[index])
        if index and (
            _comment(row, comment_at) or (x is not None and previous is not None and x < previous)
        ):
            found.append(index)
        if x is not None:
            previous = x
    return found


def _comment(row: list[str], comment_at: int | None) -> bool:
    return comment_at is not None and len(row) > comment_at and bool(row[comment_at])


def _x(row: list[str], column: int | None, decimal: str, line: int) -> float | None:
    if column is None or not row[column].strip(" \t"):
        return None
    return parse_number(row[column], decimal, line)

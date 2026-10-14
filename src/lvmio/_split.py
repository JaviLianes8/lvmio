"""Where a later write starts inside the rows of one segment header.

With "one header only" LabVIEW appends each later write to the rows of the first segment.
A later write shows as a row after the first that carries a comment, or whose X value is
not the previous X value plus the increment (it restarts, jumps or changes step); lvmio
starts a new segment there so no comment, X origin or increment is lost.
"""

from __future__ import annotations

import math

from ._number import parse_number


def starts(
    rows: list[list[str]],
    numbers: list[int],
    x_column: int | None,
    comment_at: int | None,
    decimal: str,
    delta_x: float,
) -> list[int]:
    """Row indexes that begin a segment, the first always 0."""
    found = [0]
    step = delta_x
    previous: tuple[float, float] | None = None
    for index, row in enumerate(rows):
        x = cell_value(row, x_column, decimal, numbers[index])
        jump = x is not None and previous is not None and not close(previous, x, step)
        if index and (_comment(row, comment_at) or jump):
            found.append(index)
            step = own_step(rows, index, x_column, decimal, numbers, delta_x)
        if x is not None:
            previous = x
    return found


def own_step(
    rows: list[list[str]],
    index: int,
    column: int | None,
    decimal: str,
    numbers: list[int],
    delta_x: float,
) -> float:
    """The increment of the write starting at ``index``: from its X cells when they differ."""
    if index + 1 >= len(rows):
        return delta_x
    first = cell_value(rows[index], column, decimal, numbers[index])
    second = cell_value(rows[index + 1], column, decimal, numbers[index + 1])
    if first is None or second is None or close(first, second, delta_x):
        return delta_x
    return second[0] - first[0]


def close(previous: tuple[float, float], x: tuple[float, float], step: float) -> bool:
    """Whether ``x`` follows ``previous`` by ``step``, within the cells' printed resolution."""
    rounding = 2 * math.ulp(max(abs(previous[0]), abs(x[0])))
    slack = 0.25 * abs(step) + 2 * (previous[1] + x[1]) + rounding
    return abs(x[0] - (previous[0] + step)) <= slack


def cell_value(
    row: list[str], column: int | None, decimal: str, line: int
) -> tuple[float, float] | None:
    """An X cell as (value, resolution of its last printed digit), or None when empty."""
    if column is None:
        return None
    text = row[column].strip(" \t")
    if not text:
        return None
    value = parse_number(text, decimal, line)
    if not math.isfinite(value):
        return None
    mantissa, _, exponent = text.upper().replace(decimal, ".").partition("E")
    digits = len(mantissa.partition(".")[2])
    power = int(exponent) if exponent.lstrip("+-").isdigit() else 0
    return value, 10.0 ** (power - digits)


def trim_to_samples(data: list[float], cells: list[str], samples: str | None) -> list[float]:
    """Drop the empty cells past a channel's ``Samples`` count: padding of a shorter channel.

    Only empty cells are dropped, so data past the count (a later write) is kept.
    """
    if samples is None or not samples.isdigit() or int(samples) >= len(data):
        return data
    count = int(samples)
    if any(cell.strip(" \t") for cell in cells[count:]):
        return data
    return data[:count]


def _comment(row: list[str], comment_at: int | None) -> bool:
    return comment_at is not None and len(row) > comment_at and bool(row[comment_at])

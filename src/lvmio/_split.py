"""Where a later write starts inside the rows of one segment header.

With "one header only" LabVIEW appends each later write to the rows of the first segment.
A later write shows as a row after the first that carries a comment, or whose X value is
not the previous X value plus the increment (it restarts, jumps or changes step); lvmio
starts a new segment there so no comment, X origin or increment is lost. What counts as
"not the increment" is judged from the digits the cells are printed with.
"""

from __future__ import annotations

import math

from ._number import parse_number

Cell = tuple[float, float]  # a value and the size of its last printed digit


def starts(
    rows: list[list[str]],
    numbers: list[int],
    x_column: int | None,
    comment_at: int | None,
    decimal: str,
    step: Cell,
) -> list[int]:
    """Row indexes that begin a segment, the first always 0."""
    found = [0]
    current = step
    previous: Cell | None = None
    for index, row in enumerate(rows):
        x = cell_value(row, x_column, decimal, numbers[index])
        jump = x is not None and previous is not None and not close(previous, x, current)
        if index and (_comment(row, comment_at) or jump):
            found.append(index)
            current = own_step(rows[index:], x_column, decimal, numbers[index:], step)
        if x is not None:
            previous = x
    return found


def own_step(
    rows: list[list[str]], column: int | None, decimal: str, numbers: list[int], step: Cell
) -> Cell:
    """The increment of the write starting at ``rows[0]``.

    Its own X cells give it only when two consecutive steps agree and are not zero;
    otherwise the header's increment stands.
    """
    cells = [cell_value(r, column, decimal, n) for r, n in zip(rows[:3], numbers[:3], strict=True)]
    if len(cells) < 2 or cells[0] is None or cells[1] is None:
        return step
    a, b = cells[0], cells[1]
    own = (_rounded(b[0] - a[0], max(a[1], b[1])), a[1] + b[1])
    if own[0] == 0 or close(a, b, step):
        return step
    # A third row must step the same way, so a one-row write never lends the next one's step;
    # with only two rows left, both samples keep their X values either way.
    if len(cells) == 3 and (cells[2] is None or not close(b, cells[2], own)):
        return step
    return own


def _rounded(value: float, digit: float) -> float:
    """A step from two X cells, rounded to the digits the cells are printed with."""
    if not 0 < digit < 1 or not math.isfinite(digit):
        return value
    return round(value, round(-math.log10(digit)))


def close(previous: Cell, x: Cell, step: Cell) -> bool:
    """Whether ``x`` is ``previous`` plus ``step``, within what the printed digits allow."""
    rounding = 4 * math.ulp(max(abs(previous[0]), abs(x[0]), abs(step[0])))
    slack = 0.5 * step[1] + previous[1] + x[1] + rounding
    return abs(x[0] - (previous[0] + step[0])) <= slack


def cell_value(row: list[str], column: int | None, decimal: str, line: int) -> Cell | None:
    """An X cell as (value, size of its last printed digit), or None when empty."""
    if column is None:
        return None
    text = row[column].strip(" \t")
    if not text:
        return None
    value = parse_number(text, decimal, line)
    if not math.isfinite(value):
        return None
    return value, resolution(text, decimal)


def resolution(text: str, decimal: str) -> float:
    """The size of the last printed digit of a number cell (``0.000488`` gives 1e-6)."""
    mantissa, _, exponent = text.strip(" \t").upper().replace(decimal, ".").partition("E")
    digits = len(mantissa.partition(".")[2])
    sign = -1 if exponent.startswith("-") else 1
    power = exponent.lstrip("+-")
    if not (power.isascii() and power.isdigit()):
        return 10.0**-digits
    if len(power) > 4:
        return math.inf if sign > 0 else 0.0
    try:
        return 10.0 ** (sign * int(power) - digits)
    except OverflowError:
        return math.inf


def trim_to_samples(data: list[float], cells: list[str], samples: str | None) -> list[float]:
    """Drop the empty cells past a channel's ``Samples`` count: padding of a shorter channel.

    Only empty cells are dropped, so data past the count (a later write) is kept.
    """
    if samples is None or not (samples.isascii() and samples.isdigit()) or len(samples) > 18:
        return data
    count = int(samples)
    if count >= len(data) or any(cell.strip(" \t") for cell in cells[count:]):
        return data
    return data[:count]


def _comment(row: list[str], comment_at: int | None) -> bool:
    return comment_at is not None and len(row) > comment_at and bool(row[comment_at].strip())

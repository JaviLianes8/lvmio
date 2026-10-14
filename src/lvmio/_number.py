"""Number text as LabVIEW writes it to, and reads it from, measurement files."""

from __future__ import annotations

import math
import re

from ._errors import LvmError

_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_SPECIAL = {"nan": math.nan, "inf": math.inf, "infinity": math.inf}


def format_number(value: float, decimals: int, decimal: str) -> str:
    """Format a sample the way LabVIEW's measurement file writer does.

    Fixed notation for zero and magnitudes from 1e-4 up to 1e7, exponent notation
    with an unpadded exponent otherwise, and ``NaN``, ``Inf`` and ``-Inf``.

    >>> format_number(2.5, 6, ".")
    '2.500000'
    >>> format_number(1.5e-7, 6, ",")
    '1,500000E-7'
    >>> format_number(float("-inf"), 6, ".")
    '-Inf'
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0 or 1e-4 <= abs(value) < 1e7:
        text = f"{value:.{decimals}f}"
    else:
        mantissa, exponent = f"{value:.{decimals}E}".split("E")
        text = f"{mantissa}E{int(exponent):+d}"
    return text if decimal == "." else text.replace(".", decimal)


def format_x0(value: float, decimal: str) -> str:
    """Format an ``X0`` value with the 17 significant digits LabVIEW writes there.

    >>> format_x0(0.0, ",")
    '0,0000000000000000E+0'
    """
    if not math.isfinite(value):
        return format_number(value, 0, decimal)
    mantissa, exponent = f"{value:.16E}".split("E")
    text = f"{mantissa}E{int(exponent):+d}"
    return text if decimal == "." else text.replace(".", decimal)


def parse_number(text: str, decimal: str, line: int) -> float:
    """Read one number cell; a period is always accepted as the decimal point.

    LabVIEW itself writes periods into a file declaring a comma when its writer is set
    to a period on a comma locale, so both are read. Anything that is not a whole
    number (``1_0``, ``0x10``, ``2.5V``) is refused rather than read in part.

    >>> parse_number("2,5E-3", ",", 1)
    0.0025
    >>> parse_number("-Inf", ".", 1)
    -inf
    """
    token = text.strip(" \t")
    if decimal != ".":
        token = token.replace(decimal, ".", 1)
    sign = -1.0 if token[:1] == "-" else 1.0
    special = _SPECIAL.get(token.lstrip("+-").lower())
    if special is not None and len(token) - len(token.lstrip("+-")) <= 1:
        return sign * special
    if _NUMBER.fullmatch(token) is None:
        raise LvmError(f"line {line}: not a number: {shorten(text)}")
    return float(token)


def shorten(text: str, limit: int = 40) -> str:
    """The repr of ``text``, cut to ``limit`` characters so messages stay short.

    >>> shorten("x" * 50, 5)
    "'xxxxx'... (50 characters)"
    """
    if len(text) <= limit:
        return repr(text)
    return f"{text[:limit]!r}... ({len(text)} characters)"

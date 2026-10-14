"""Number text as LabVIEW writes it to, and reads it from, measurement files."""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal

from ._errors import LvmError

_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
# Decimal exponents at which LabVIEW 2026 rounds an exact tie in exponent notation toward
# zero; at every other exponent it rounds away from zero (measured for 7 to 19, the only
# exponents where a double can hold a tie exactly).
_TIES_TOWARD_ZERO = frozenset({11, 16, 17})
_SPECIAL = {"nan": math.nan, "inf": math.inf, "infinity": math.inf}


def format_number(value: float, decimals: int, decimal: str) -> str:
    """Format a sample the way LabVIEW's measurement file writer does.

    The notation follows ``floor(log10(|value|))`` computed in double precision: fixed
    from -4 to 6, exponent notation (unpadded exponent) otherwise. Fixed notation rounds
    the exact binary value with ties toward zero; exponent notation rounds ties away from
    zero, except at the decimal exponents 11, 16 and 17, as LabVIEW 2026 does. NaN and
    the infinities are ``NaN``, ``Inf`` and ``-Inf``.

    >>> format_number(2.5, 6, ".")
    '2.500000'
    >>> format_number(1.5e-7, 6, ",")
    '1,500000E-7'
    >>> format_number(0.0234375, 6, "."), format_number(10000005.0, 6, ".")
    ('0.023437', '1.000001E+7')
    >>> format_number(float("-inf"), 6, ".")
    '-Inf'
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    sign = "-" if math.copysign(1.0, value) < 0 else ""
    size = abs(value)
    exponent = math.floor(math.log10(size)) if size else 0
    step = Decimal(1).scaleb(-decimals)
    if -4 <= exponent < 7:
        text = f"{Decimal(size).quantize(step, rounding=ROUND_HALF_DOWN):f}"
    else:
        mode = ROUND_HALF_DOWN if exponent in _TIES_TOWARD_ZERO else ROUND_HALF_UP
        mantissa = Decimal(size).scaleb(-exponent).quantize(step, rounding=mode)
        if mantissa >= 10:
            mantissa = (mantissa / 10).quantize(step, rounding=mode)
            exponent += 1
        text = f"{mantissa:f}E{exponent:+d}"
    text = sign + text
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
    if len(text) <= limit and len(repr(text)) <= limit + 22:
        return repr(text)
    quoted = repr(text[:limit])[: limit + 20]
    return f"{quoted}... ({len(text)} characters)"

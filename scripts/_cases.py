"""The values and comments given to LabVIEW's writer, and the cells given to its reader."""

from __future__ import annotations

import math
import random
from decimal import Decimal

EDGES = [
    0.0,
    -0.0,
    1e-4,
    9.99999e-5,
    1e7,
    9999999.0,
    9999999.4,
    9999999.6,
    0.0001000004,
    1e-320,
    5e-324,
    1.7976931348623157e308,
    2.2250738585072014e-308,
    0.5,
    123.4567895,
]
COMMENTS = [
    "C:\\data\\new\\t1",
    "a\\b",
    "50% done",
    "x,y;z",
    "tab\there",
    "cr\rlf\nend",
    "\x01\x1f\x7f",
    "  padded  ",
    "quote \"q\" 'q'",
    "\\0D kept",
    "Channels",
    "end\\",
]
TOKENS = [
    "NaN",
    "Inf",
    "-Inf",
    "nan",
    "inf",
    "+2.5",
    ".5",
    "5.",
    "-0",
    "1.5e-7",
    "1E+300",
    "1e-300",
    "0x10",
    "1_0",
    " 7 ",
    "abc",
    "1,5",
    "Infinity",
    "1e400",
    "2.5V",
    "-nan",
    "+NaN",
    "   ",
    "1.5e",
    "1d5",
    "Inf5",
    "NaN1",
    "1E5.5",
    "1.#INF",
    "nan(ind)",
    "0b1",
    "1e5e5",
    "Infinite",
    "infinityx",
    "1 2",
    "\u2212" + "1",
    chr(12) + "1",
    chr(12) + "1" + chr(12),
    " " + chr(12) + "2.5",
    "- 1",
    "+ 2",
    "- Inf",
    "1e+ 5",
]

# Later writes in "one header only" mode whose X jumps forward or changes step.
ONE_HEADER_LATER = {
    "gap": {"rows": [[0.0] * 6 + [7.0, 8.0, 9.0]], "dt": 1.0, "start": 6, "headings": 1},
    "step": {"rows": [[0.0] * 6 + [7.0, 8.0, 9.0]], "dt": 0.5, "start": 6, "headings": 1},
}


def x0_offsets(seed: int = 8208, count: int = 60) -> list[dict[str, object]]:
    """Waveforms whose start sample moves X0 to a non-zero time, one segment each."""
    rng = random.Random(seed)
    steps: list[dict[str, object]] = []
    for _ in range(count):
        dt = rng.choice([1 / 96000, 1 / 44100, 1 / 3, 1e-3, 0.1, 1 / 7, 2.5e-5, 1 / 1024, 0.3])
        start = rng.randint(1, 5000)
        steps.append({"rows": [[0.0] * (start + 2)], "dt": dt, "start": start})
    return steps


def numbers(seed: int = 2026, count: int = 400) -> list[list[float]]:
    """Seeded magnitudes across the double range plus the format boundaries."""
    rng = random.Random(seed)
    values = EDGES + [-v for v in EDGES]
    while len(values) < count:
        values.append(rng.choice((-1, 1)) * rng.uniform(1, 10) * 10.0 ** rng.randint(-310, 307))
    return [values[i::4] for i in range(4)]


def ties(seed: int = 77) -> list[list[float]]:
    """Exact rounding ties in both notations and values next to the notation boundaries."""
    rng = random.Random(seed)
    fixed = [k / 128 for k in range(1, 256, 2)] + [1000000.0859375, -0.0546875]
    fixed += [rng.randint(-999_999, 999_999) + rng.randrange(1, 128, 2) / 128 for _ in range(126)]
    scaled = [10000005.0, 10000025.0, 67417605.0, -326254450.0, 99999995.0, 1000000500000000.0]
    scaled += [float(rng.randrange(10_000_000, 99_999_999) * 10 + 5) for _ in range(120)]
    scaled += [
        -float(rng.randrange(1_000_000, 9_999_999) * 10 ** rng.randint(2, 12) + 5 * 10**1)
        for _ in range(4)
    ]
    bounds = [
        math.nextafter(1e7, 0),
        math.nextafter(1e-4, 0),
        math.nextafter(1e-4, 1),
        9999999.9999995,
        9999999.999999,
        99999.99999995,
        1e-4 * (1 + 2**-52),
        1e7 * 3,
    ]
    bounds += [-b for b in bounds]
    values = fixed + scaled + bounds
    values += [0.0] * (-len(values) % 4)
    return [values[i::4] for i in range(4)]


def exponent_ties(seed: int = 711) -> list[list[float]]:
    """Exact ties in exponent notation: up to twelve per decimal exponent from 7 to 19.

    A tie needs an odd eight-digit integer times a power of ten held exactly in a double,
    which stops being possible above 1e19.
    """
    rng = random.Random(seed)
    values: list[float] = []
    for exponent in range(7, 20):
        found = tries = 0
        while found < 12 and tries < 200_000:
            tries += 1
            exact = Decimal(rng.randrange(1_000_000, 10_000_000) * 10 + 5).scaleb(exponent - 7)
            value = float(exact)
            if Decimal(value) == exact:
                values.append(value if found % 2 else -value)
                found += 1
    values += [0.0] * (-len(values) % 4)
    return [values[i::4] for i in range(4)]


def near_ties(seed: int = 712, count: int = 400) -> list[list[float]]:
    """The doubles nearest to halfway points, over the whole exponent range."""
    rng = random.Random(seed)
    values = [9.9999995e-239, 9.9999995e119, 9.99999996e-5, -9.99999996e-5]
    while len(values) < count:
        digits = rng.randrange(1_000_000, 10_000_000) * 10 + 5
        values.append(float(f"{digits}e{rng.randint(-300, 290)}"))
    return [values[i::4] for i in range(4)]

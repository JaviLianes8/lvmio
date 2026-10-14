"""The values and comments given to LabVIEW's writer, and the cells given to its reader."""

from __future__ import annotations

import math
import random

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
]


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

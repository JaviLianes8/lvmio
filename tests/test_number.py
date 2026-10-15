"""The number text rules: LabVIEW's writer format and the reader's grammar."""

from __future__ import annotations

import math
import random

import pytest

from lvmio import LvmError, format_lvm, parse_lvm
from lvmio._number import format_number, format_x0, parse_number


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0.0, "0.000000"),
        (-0.0, "-0.000000"),
        (1e-4, "0.000100"),
        (9.99999e-5, "9.999990E-5"),
        (9999999.6, "9999999.600000"),
        (1e7, "1.000000E+7"),
        (-1e7, "-1.000000E+7"),
        (1e300, "1.000000E+300"),
        (5e-324, "4.940656E-324"),
        (math.nan, "NaN"),
        (math.inf, "Inf"),
        (-math.inf, "-Inf"),
    ],
)
def test_format_number_follows_labview(value: float, text: str) -> None:
    assert format_number(value, 6, ".") == text
    assert format_number(value, 6, ",") == text.replace(".", ",")


def test_precision_changes_the_decimals_in_both_notations() -> None:
    assert format_number(2.5, 2, ".") == "2.50"
    assert format_number(1.25e-9, 0, ".") == "1E-9"
    assert format_number(1 / 3, 17, ".") == "0.33333333333333331"


def test_x0_keeps_17_significant_digits() -> None:
    assert format_x0(0.1, ".") == "1.0000000000000001E-1"
    assert format_x0(-2.5, ",") == "-2,5000000000000000E+0"
    assert float(format_x0(1 / 3, ".")) == 1 / 3


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1", 1.0),
        ("+2.5", 2.5),
        (".5", 0.5),
        ("5.", 5.0),
        ("-0", -0.0),
        ("1.5e-7", 1.5e-7),
        ("1E+300", 1e300),
        ("1e400", math.inf),
        (" 7 ", 7.0),
        ("\t7", 7.0),
        ("NaN", math.nan),
        ("-nan", math.nan),
        ("Inf", math.inf),
        ("-Infinity", -math.inf),
        ("+inf", math.inf),
    ],
)
def test_parse_number_reads_whole_numbers(text: str, value: float) -> None:
    got = parse_number(text, ".", 3)
    assert (math.isnan(got) and math.isnan(value)) or got == value
    assert math.copysign(1, got) == math.copysign(1, value) or math.isnan(value)


@pytest.mark.parametrize(
    "text",
    [
        "1_0",
        "0x10",
        "1,5",
        "2.5V",
        "abc",
        "--1",
        "+-1",
        "1e",
        "e5",
        ".",
        "1.2.3",
        "\u0661",
        "1 2",
        "++inf",
        "nan(1)",
        "infin",
        "1e+",
        "\u00a07",
        "\u20077",
    ],
)
def test_parse_number_refuses_everything_else(text: str) -> None:
    with pytest.raises(LvmError, match=r"^line 3: not a number: "):
        parse_number(text, ".", 3)


def test_a_comma_file_reads_commas_and_periods() -> None:
    assert parse_number("2,5", ",", 1) == 2.5
    assert parse_number("2.5", ",", 1) == 2.5
    assert parse_number("-1,5E-3", ",", 1) == -0.0015
    with pytest.raises(LvmError):
        parse_number("1,5,0", ",", 1)


def test_the_grammar_check_is_linear() -> None:
    import time

    start = time.perf_counter()
    for size in (10_000, 200_000):
        with pytest.raises(LvmError):
            parse_number("1" * size + "x", ".", 1)
        with pytest.raises(LvmError):
            parse_number("1." + "1" * size + "e", ".", 1)
    assert time.perf_counter() - start < 2.0


def test_seeded_round_trip_through_the_writer_and_reader() -> None:
    rng = random.Random(7)
    values = [rng.uniform(-1, 1) * 10.0 ** rng.randint(-320, 307) for _ in range(3000)]
    values += [math.nan, math.inf, -math.inf, 0.0, -0.0]
    for decimal in (".", ","):
        text = format_lvm({"v": values}, precision=17, decimal_separator=decimal)
        back = parse_lvm(text).segments[0].channels[0].data
        for value, read in zip(values, back, strict=True):
            expected = float(format_number(value, 17, "."))
            assert (math.isnan(value) and math.isnan(read)) or read == expected
            if math.isfinite(value) and not 1e-4 <= abs(value) < 1e7:
                assert read == value

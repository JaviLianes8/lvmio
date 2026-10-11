"""Golden tests against the committed genuine LabVIEW fixtures.

These files were written by real NI software (their headers say "LabVIEW
Measurement", Writer_Version 2). They lock in the exact behaviour on real output.
"""

import math
from pathlib import Path

import pytest

from lvmio import read_lvm

FIXTURES = Path(__file__).parent / "fixtures"


def test_short_tab_decimal_comma() -> None:
    lvm = read_lvm(FIXTURES / "short.lvm")
    assert lvm.separator == "Tab"
    assert lvm.decimal_separator == ","
    assert lvm.time_pref == "Absolute"
    channel = lvm.segments[0]["Response (Trigger)"]
    assert channel.unit == "m/s^2"
    assert channel.delta_x == pytest.approx(3.906250e-5)
    assert len(channel) == 10
    assert channel.data[-1] == pytest.approx(1.212775)


def test_comma_separated_file() -> None:
    lvm = read_lvm(FIXTURES / "comma_separator.lvm")
    assert lvm.separator == "Comma"
    assert lvm.decimal_separator == "."
    assert lvm.segments[0].names == ["p_st1", "p_st2", "p_plate", "TC1"]
    assert lvm.segments[0]["TC1"].data[0] == pytest.approx(0.163976)


def test_comments_on_some_rows_do_not_corrupt_channels() -> None:
    lvm = read_lvm(FIXTURES / "comments_on_some_rows.lvm")
    channel = lvm.segments[0]["Excitation (Trigger)"]
    assert len(channel) == 10
    assert channel.data[2] == pytest.approx(0.616905)
    assert not any(math.isnan(v) for v in channel.data)


def test_with_empty_fields_yields_nan_channels() -> None:
    lvm = read_lvm(FIXTURES / "with_empty_fields.lvm")
    segment = lvm.segments[0]
    assert segment.names == [
        "Dev0/Ai0",
        "Dev0/Ai2",
        "Untitled",
        "Untitled 1",
        "Untitled 2",
        "Untitled 3",
        "Dev0/Ai0 1",
    ]
    assert all(math.isnan(v) for v in segment["Untitled 3"].data)
    assert segment["Dev0/Ai2"].data[0] == pytest.approx(7.254639)


def test_time_axis_from_real_x0_delta_x() -> None:
    lvm = read_lvm(FIXTURES / "comma_separator.lvm")
    axis = lvm.segments[0]["p_st1"].time_axis()
    assert axis[0] == pytest.approx(0.0)
    assert axis[1] == pytest.approx(2.0e-6)
    assert len(axis) == 4

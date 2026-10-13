"""Golden tests against the committed hand-made fixtures.

``scripts/make_lvm_fixtures.py`` writes these files from formulas, in the layouts real
LabVIEW output uses (tab or comma separator, decimal comma, an empty X column, row
comments, empty channels). They lock in the exact behaviour on those layouts.
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
    channel = lvm.segments[0]["Accel (Frame)"]
    assert channel.unit == "m/s^2"
    assert channel.delta_x == pytest.approx(2.5e-4)
    assert len(channel) == 10
    assert channel.data[-1] == pytest.approx(1.195129)


def test_comma_separated_file() -> None:
    lvm = read_lvm(FIXTURES / "comma_separator.lvm")
    assert lvm.separator == "Comma"
    assert lvm.decimal_separator == "."
    assert lvm.segments[0].names == ["inlet", "outlet", "chamber", "T1"]
    assert lvm.segments[0]["T1"].data[0] == pytest.approx(0.25)


def test_comments_on_some_rows_do_not_corrupt_channels() -> None:
    lvm = read_lvm(FIXTURES / "comments_on_some_rows.lvm")
    channel = lvm.segments[0]["Load (Cell A)"]
    assert len(channel) == 10
    assert channel.data[2] == pytest.approx(0.894180)
    assert not any(math.isnan(v) for v in channel.data)


def test_with_empty_fields_yields_nan_channels() -> None:
    lvm = read_lvm(FIXTURES / "with_empty_fields.lvm")
    segment = lvm.segments[0]
    assert segment.names == [
        "Dev1/ai0",
        "Dev1/ai1",
        "Spare",
        "Spare 1",
        "Spare 2",
        "Spare 3",
        "Dev1/ai0 1",
    ]
    assert all(math.isnan(v) for v in segment["Spare 3"].data)
    assert segment["Dev1/ai1"].data[0] == pytest.approx(5.0)


def test_time_axis_from_x0_and_delta_x() -> None:
    lvm = read_lvm(FIXTURES / "comma_separator.lvm")
    axis = lvm.segments[0]["inlet"].time_axis()
    assert axis[0] == pytest.approx(0.0)
    assert axis[1] == pytest.approx(5.0e-6)
    assert len(axis) == 4

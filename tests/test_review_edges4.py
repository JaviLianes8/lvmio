"""Contracts from the third combined review of hostile input and documentation."""

from __future__ import annotations

import decimal
import time
from pathlib import Path

import pytest

from lvmio import Channel, format_lvm, parse_lvm, write_lvm
from lvmio._number import format_number

HEAD = "LabVIEW Measurement\t\nSeparator\tTab\nDecimal_Separator\t.\n"


@pytest.mark.parametrize(
    ("x0", "dx", "count"),
    [(-1.0, 0.001, 2000), (-100.0, 0.1, 3000), (-0.001, 1e-6, 3000), (5.0, -0.001, 10000)],
)
@pytest.mark.parametrize("precision", [14, 15, 16, 17])
def test_an_axis_heading_toward_zero_stays_one_segment(
    x0: float, dx: float, count: int, precision: int
) -> None:
    channel = Channel("V", [float(i) for i in range(count)], x0=x0, delta_x=dx)
    text = format_lvm([channel], precision=precision)
    lvm = parse_lvm(text)
    assert len(lvm) == 1
    assert format_lvm(lvm, precision=precision) == text


def test_a_logging_loop_of_one_row_per_write_reads_in_linear_time() -> None:
    head = HEAD + "X_Columns\tOne\n***End_of_Header***\t\n\t\n"
    seg = "Channels\t1\t\nSamples\t1\t\nX0\t0\t\nDelta_X\t1\t\n***End_of_Header***\t\t\n"

    def seconds(rows: int) -> float:
        lines = "".join(f"0.000000\t{i}\t\n" for i in range(rows))
        best = float("inf")
        for _ in range(2):
            began = time.perf_counter()
            lvm = parse_lvm(head + seg + "X_Value\tV\tComment\n" + lines)
            best = min(best, time.perf_counter() - began)
        assert len(lvm) == rows
        return best

    # Four times the rows; copying the remaining rows at every write made it about 11 times.
    assert seconds(40000) < 7 * seconds(10000)


def test_the_callers_decimal_context_does_not_change_what_is_written() -> None:
    expected = format_lvm({"a": [1.5, 1.0000004999999e-5, 1e300, 9.9999995e-5]})
    with decimal.localcontext() as ctx:
        ctx.prec = 5
        ctx.traps[decimal.Inexact] = True
        ctx.traps[decimal.Rounded] = True
        assert format_lvm({"a": [1.5, 1.0000004999999e-5, 1e300, 9.9999995e-5]}) == expected
    with decimal.localcontext() as ctx:
        ctx.prec = 10
        assert format_number(1.0000004999999e-5, 6, ".") == "1.000000E-5"


def test_a_jump_in_a_later_multi_x_column_starts_a_segment() -> None:
    head = HEAD + "X_Columns\tMulti\n***End_of_Header***\t\n\n"
    seg = "Channels\t2\nDelta_X\t1\t\t1\n***End_of_Header***\t\n"
    rows = "0\t1\t0\t1\n1\t2\t1\t2\n2\t3\t50\t3\n"
    lvm = parse_lvm(head + seg + "X_Value\tA\tX_Value\tB\tComment\n" + rows)
    found = [[(c.name, c.x0, c.data) for c in s.channels] for s in lvm]
    assert found == [
        [("A", 0.0, [1.0, 2.0]), ("B", 0.0, [1.0, 2.0])],
        [("A", 2.0, [3.0]), ("B", 50.0, [3.0])],
    ]


def test_samples_padding_of_the_first_write_is_trimmed_when_a_later_write_follows() -> None:
    head = HEAD + "X_Columns\tOne\n***End_of_Header***\t\n\n"
    seg = "Channels\t2\nSamples\t4\t2\n***End_of_Header***\t\n"
    rows = "0\t1\t1\n1\t2\t2\n2\t3\t\n3\t4\t\tlater\n"
    lvm = parse_lvm(head + seg + "X_Value\tA\tB\tComment\n" + rows)
    b = [s.channels[1].data for s in lvm]
    assert b[0] == [1.0, 2.0]
    assert len(b) == 2 and len(b[1]) == 1


@pytest.mark.parametrize("encoding", ["idna", "undefined"])
def test_an_encoding_that_fails_without_a_position_names_no_character(
    encoding: str, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match=f"^the text cannot be written as {encoding}$"):
        write_lvm(tmp_path / "x.lvm", {"a": [1.0]}, encoding=encoding)
    assert not (tmp_path / "x.lvm").exists()

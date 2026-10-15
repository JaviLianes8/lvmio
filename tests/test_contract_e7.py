"""Contracts from the seventh blind mutation review: each pins one behaviour."""

from __future__ import annotations

import contextlib
import decimal
import io
from pathlib import Path

import pytest

import lvmio
from lvmio._cli_output import _print_channels
from lvmio._number import format_number

HEAD = "LabVIEW Measurement\t\n***End_of_Header***\t\n\n"


def test_a_write_without_a_step_of_its_own_falls_back_to_the_header_step() -> None:
    # The second write steps by 2; the third (100, 101, 103) has no confirmed step of its own,
    # so it is judged by the header's 1, not by the 2 of the write before it.
    xs = [0, 1, 2, 10, 12, 14, 100, 101, 103]
    rows = "".join(f"{x}.000\t1\n" for x in xs)
    seg = "Channels\t1\nDelta_X\t1.000\n***End_of_Header***\t\n"
    text = HEAD + seg + "X_Value\tV\tComment\n" + rows
    assert [s["V"].x0 for s in lvmio.parse_lvm(text)] == [0.0, 10.0, 100.0, 103.0]


def test_every_x_column_takes_the_step_of_the_new_write() -> None:
    head = "LabVIEW Measurement\t\nX_Columns\tMulti\n***End_of_Header***\t\n\n"
    seg = "Channels\t2\nDelta_X\t1.000\t\t1.000\n***End_of_Header***\t\n"
    pairs = [(0, 0), (1, 1), (2, 2), (10, 10), (11, 12), (12, 14)]
    rows = "".join(f"{a}.000\t{i}\t{b}.000\t{i}\n" for i, (a, b) in enumerate(pairs, 1))
    lvm = lvmio.parse_lvm(head + seg + "X_Value\tA\tX_Value\tB\tComment\n" + rows)
    found = [[(c.x0, c.delta_x, c.data) for c in s] for s in lvm]
    assert found == [
        [(0.0, 1.0, [1.0, 2.0, 3.0]), (0.0, 1.0, [1.0, 2.0, 3.0])],
        [(10.0, 1.0, [4.0, 5.0, 6.0]), (10.0, 2.0, [4.0, 5.0, 6.0])],
    ]


def test_an_x_column_after_the_last_channel_is_not_read() -> None:
    columns = "X_Value\tV\tX_Value\tComment\n"
    text = HEAD + "Channels\t1\n***End_of_Header***\t\n" + columns + "0\t1.5\n1\t2.5\n"
    segments = lvmio.parse_lvm(text).segments
    assert [(s.names, s["V"].data) for s in segments] == [(["V"], [1.5, 2.5])]


def test_first_write_padding_is_trimmed_even_when_a_later_write_fills_that_column() -> None:
    seg = "Channels\t2\nSamples\t3\t2\n***End_of_Header***\t\n"
    rows = "0\t1\t1\n1\t2\t2\n2\t3\t\n10\t4\t4\tlater\n"
    lvm = lvmio.parse_lvm(HEAD + seg + "X_Value\tA\tB\tComment\n" + rows)
    assert [s["B"].data for s in lvm] == [[1.0, 2.0], [4.0]]


def test_a_mantissa_carried_to_ten_ignores_the_callers_decimal_context() -> None:
    with decimal.localcontext() as ctx:
        ctx.prec = 3
        ctx.traps[decimal.Rounded] = True
        assert format_number(99999999999.99, 6, ".") == "1.000000E+11"


def test_an_unknown_encoding_of_forty_characters_is_named_unquoted(tmp_path: Path) -> None:
    name = "x" * 40
    with pytest.raises(LookupError) as info:
        lvmio.read_lvm(tmp_path / "missing.lvm", encoding=name)
    assert str(info.value) == f"unknown encoding: {name}"


def test_the_channel_list_escapes_control_characters_in_units() -> None:
    lvm = lvmio.LvmFile([lvmio.Segment([lvmio.Channel("A", [1.0], unit="V\x1b[2J")])])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _print_channels(lvm)
    assert out.getvalue() == "segment 0: 1 channel, 1 sample\n  A [V\\1B[2J]: 1 sample\n"

"""Contracts from the fifth blind mutation review: each pins one behaviour."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lvmio import LvmError, format_lvm, parse_lvm, read_lvm
from lvmio._cli import main

HEAD = "LabVIEW Measurement\t\n***End_of_Header***\t\n\n"


def test_explicit_encoding_error_names_the_first_bad_byte(tmp_path: Path) -> None:
    path = tmp_path / "bad.lvm"
    path.write_bytes(b"LabVIEW Measurement\t\r\n\xff")
    with pytest.raises(LvmError) as info:
        read_lvm(path, encoding="utf-8")
    assert str(info.value) == "not utf-8 text at byte 22"


def test_fallback_decoding_error_names_the_first_bad_byte(tmp_path: Path) -> None:
    path = tmp_path / "bad.lvm"
    path.write_bytes(b"LabVIEW Measurement\t\r\n\x81")
    with pytest.raises(LvmError) as info:
        read_lvm(path)
    assert str(info.value) == "neither UTF-8 nor Windows-1252 text at byte 22"


def test_first_line_must_be_exactly_the_magic_text() -> None:
    with pytest.raises(LvmError, match="not a LabVIEW Measurement file"):
        parse_lvm("LabVIEW MeasurementX\t\n***End_of_Header***\t\n")


def test_a_value_under_a_lone_x_value_column_is_refused() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nX_Value\n1.0\n"
    with pytest.raises(LvmError, match="a cell after the last column"):
        parse_lvm(text)


def test_without_an_x_column_a_later_write_starts_at_x0_plus_its_offset() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nV\tComment\n1\t\n5\tc2\n9\t\n"
    later = parse_lvm(text).segments[1]
    assert later.comment == "c2"
    assert (later["V"].x0, later["V"].data) == (1.0, [5.0, 9.0])


def test_segment_date_is_the_first_channel_date_cell() -> None:
    text = (
        HEAD + "Channels\t1\nDate\td1\td2\n***End_of_Header***\t\n"
        "X_Value\tX_Value\tV\tComment\n0\t0\t1\n"
    )
    segment = parse_lvm(text).segments[0]
    assert (segment.date, segment["V"].date) == ("d2", "d2")


def test_a_later_write_whose_third_x_cell_is_empty_keeps_the_header_step() -> None:
    text = (
        HEAD + "Channels\t1\nDelta_X\t1.000000\n***End_of_Header***\t\nX_Value\tV\tComment\n"
        "0.000000\t1\n1.000000\t1\n2.000000\t1\n10.000000\t2\n10.500000\t2\n\t2\n"
    )
    got = [(c.x0, c.delta_x, c.data) for s in parse_lvm(text) for c in s]
    assert got == [(0.0, 1.0, [1.0] * 3), (10.0, 1.0, [2.0]), (10.5, 1.0, [2.0, 2.0])]


def test_a_sequence_that_is_not_channels_is_refused_before_the_keywords() -> None:
    bad: Any = [1.0]
    with pytest.raises(TypeError, match="expected Channel objects, got float"):
        format_lvm(bad, separator="Pipe")


def test_an_unreadable_path_error_names_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "d").mkdir()
    assert main(["header", "d"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("lvmio: error: ")
    assert err.endswith(": 'd'\n")
    assert len(err) > len("lvmio: error: : 'd'\n")

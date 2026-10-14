"""What the writer refuses, with which error, and that nothing is written then."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from lvmio import Channel, LvmFile, Segment, format_lvm, write_lvm


def _file(**changes: Any) -> LvmFile:
    seg = Segment([Channel("V", [1.0])])
    return LvmFile([seg], **changes)


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ("text", TypeError),
        (b"bytes", TypeError),
        (42, TypeError),
        ([1.0, 2.0], TypeError),
        ({1: [1.0]}, TypeError),
        ({"a": "123"}, TypeError),
        ({"a": [True]}, TypeError),
        ({"a": ["1.5"]}, TypeError),
        ({"a": [None]}, TypeError),
        ({"a": [1 + 2j]}, TypeError),
        (LvmFile([Segment([Channel("a", [1.0], x0="0")])]), TypeError),  # type: ignore[arg-type]
        (LvmFile([Segment(["a"])]), TypeError),  # type: ignore[list-item]
        (LvmFile(["seg"]), TypeError),  # type: ignore[list-item]
        (LvmFile([], multi_headings="Yes"), TypeError),  # type: ignore[arg-type]
        (LvmFile([], operator=None), TypeError),  # type: ignore[arg-type]
        (LvmFile([Segment([], comment=3)]), TypeError),  # type: ignore[arg-type]
        ({"": [1.0]}, ValueError),
        ({"X_Value": [1.0]}, ValueError),
        ({"comment": [1.0]}, ValueError),
        ({"a\tb": [1.0]}, ValueError),
        ({"a\nb": [1.0]}, ValueError),
        ({" a": [1.0]}, ValueError),
        (LvmFile([Segment([Channel("a", [1.0], unit="V\r")])]), ValueError),
        (LvmFile([Segment([Channel("a", [1.0], x_dimension="")])]), ValueError),
        (LvmFile([Segment([], comment="two\nlines")]), ValueError),
        (_file(operator="a\tb"), ValueError),
        (_file(separator="Semicolon"), ValueError),
        (_file(decimal_separator=";"), ValueError),
        (_file(x_columns="Two"), ValueError),
        (_file(separator="Comma", decimal_separator=","), ValueError),
        (_file(separator="Comma", operator="Smith, J"), ValueError),
    ],
)
def test_bad_data_is_refused(data: Any, error: type[Exception], tmp_path: Path) -> None:
    with pytest.raises(error):
        format_lvm(data)
    out = tmp_path / "x.lvm"
    with pytest.raises(error):
        write_lvm(out, data)
    assert not out.exists()


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"precision": -1}, ValueError),
        ({"precision": 18}, ValueError),
        ({"precision": 2.0}, TypeError),
        ({"precision": True}, TypeError),
        ({"separator": "pipe"}, ValueError),
        ({"x_columns": 1}, TypeError),
        ({"operator": 5}, TypeError),
    ],
)
def test_bad_keywords_are_refused(kwargs: dict[str, Any], error: type[Exception]) -> None:
    with pytest.raises(error):
        format_lvm({"a": [1.0]}, **kwargs)


def test_spellings_are_made_canonical() -> None:
    text = format_lvm({"a": [1.0]}, separator="comma", x_columns="multi")
    assert "Separator,Comma\r\n" in text
    assert "X_Columns,Multi\r\n" in text


def test_numbers_of_other_real_types_are_accepted() -> None:
    from decimal import Decimal  # not a numbers.Real: refused
    from fractions import Fraction

    assert "0.500000" in format_lvm({"a": [Fraction(1, 2), 3]})
    with pytest.raises(TypeError):
        format_lvm({"a": [Decimal("0.5")]})


def test_text_that_cannot_be_encoded_is_refused_before_writing(tmp_path: Path) -> None:
    out = tmp_path / "x.lvm"
    with pytest.raises(ValueError, match="cannot be written as cp1252"):
        write_lvm(out, {"\u4e2d": [1.0]}, encoding="cp1252")
    assert not out.exists()


def test_the_comment_may_hold_the_separator_and_round_trips() -> None:
    from lvmio import parse_lvm

    lvm = LvmFile([Segment([Channel("a", [1.0, 2.0])], comment="x\ty, z")])
    assert parse_lvm(format_lvm(lvm)).segments[0].comment == "x\ty, z"
    comma = format_lvm(lvm.segments[0].channels, separator="Comma")
    assert parse_lvm(comma).segments[0].comment == ""
    with_comma = LvmFile(lvm.segments, separator="Comma")
    assert parse_lvm(format_lvm(with_comma)).segments[0].comment == "x\ty, z"


def _refusals() -> list[Callable[[], object]]:
    return [lambda: format_lvm(Segment([Channel("a" * 10_000 + "\t", [1.0])]))]


def test_messages_stay_short_for_huge_input() -> None:
    for call in _refusals():
        with pytest.raises(ValueError) as info:
            call()
        assert len(str(info.value)) < 200

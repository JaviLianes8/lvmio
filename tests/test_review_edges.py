"""Contracts from the independent reviews: writer checks, reader limits, CLI bounds."""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path

import pytest
from _clirun import run

from lvmio import Channel, LvmError, LvmFile, Segment, format_lvm, parse_lvm

NBSP, VT, LS = chr(0xA0), chr(0x0B), chr(0x2028)


@pytest.mark.parametrize("blank", [NBSP, VT, LS, chr(0x85), chr(0x1F), " "])
def test_any_surrounding_blank_is_refused_so_text_reads_back_unchanged(blank: str) -> None:
    for data in ({"V" + blank: [1.0]}, {"Comment" + blank: [1.0]}):
        with pytest.raises(ValueError, match="blanks"):
            format_lvm(data)
    with pytest.raises(ValueError, match="blanks"):
        format_lvm({"V": [1.0]}, operator=blank + "lab")
    inside = "a" + NBSP + "b"
    assert parse_lvm(format_lvm({inside: [1.0]})).segments[0].names == [inside]


def test_a_comment_needs_a_row() -> None:
    with pytest.raises(ValueError, match="needs at least one data row"):
        format_lvm(Segment([Channel("V", [])], comment="hi"))
    assert parse_lvm(format_lvm(Segment([Channel("V", [])]))).segments[0].comment == ""


def test_comments_with_any_character_round_trip() -> None:
    text = "C:" + chr(92) + "new" + chr(92) + chr(92) + "x\r\n\t,end" + chr(1) + chr(0x7F)
    for separator in ("Tab", "Comma"):
        lvm = LvmFile([Segment([Channel("V", [1.0])], comment=text)], separator=separator)
        written = format_lvm(lvm)
        assert parse_lvm(written).segments[0].comment == text
        plain = LvmFile([Segment([Channel("V", [1.0])])], separator=separator)
        assert written.count("\r\n") == format_lvm(plain).count("\r\n")


def test_only_a_period_or_a_comma_is_a_decimal_separator() -> None:
    text = format_lvm({"V": [-5.0]}).replace("Decimal_Separator\t.", "Decimal_Separator\t-")
    with pytest.raises(LvmError, match="Decimal_Separator must be"):
        parse_lvm(text)


def test_a_finite_decimal_too_large_for_a_double_is_refused() -> None:
    for value in (Decimal("1e400"), Decimal("-1e400")):
        with pytest.raises(ValueError, match="too large"):
            format_lvm({"V": [value]})  # type: ignore[list-item]
    assert "Inf" in format_lvm({"V": [Decimal("Infinity")]})  # type: ignore[list-item]


@pytest.mark.parametrize("values", [{3.0, 1.0}, {1.5: "x"}, frozenset({1.0})])
def test_unordered_samples_are_refused(values: object) -> None:
    with pytest.raises(TypeError, match="ordered iterable"):
        format_lvm({"V": values})  # type: ignore[dict-item]


class _LyingStr(str):
    def __contains__(self, item: object) -> bool:
        return False

    def __format__(self, spec: str) -> str:
        return "x\r\ninjected"

    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


def test_text_subclasses_cannot_change_what_is_checked_or_written() -> None:
    with pytest.raises(ValueError):
        format_lvm({_LyingStr("a\tb"): [1.0]})
    text = format_lvm({"V": [1.0]}, operator=_LyingStr("ok"))
    assert "injected" not in text and "Operator\tok\r\n" in text
    with pytest.raises(ValueError):
        format_lvm({"V": [1.0]}, decimal_separator=_LyingStr(";"))


class _LyingInt(int):
    def __format__(self, spec: str) -> str:
        return "99"


def test_precision_is_used_as_an_exact_int_and_never_echoed() -> None:
    assert "1.50\r\n" in format_lvm({"V": [1.5]}, precision=_LyingInt(2)).replace("0.00\t", "")
    with pytest.raises(ValueError) as info:
        format_lvm({"V": [1.0]}, precision=10**4000)
    assert str(info.value) == "precision must be between 0 and 17"


def test_short_rows_are_refused_in_linear_time() -> None:
    def build(n: int) -> str:
        names = "\t".join(["v"] * n)
        head = (
            "LabVIEW Measurement\t\n***End_of_Header***\t\n\nChannels\t1\n***End_of_Header***\t\n"
        )
        return head + "X_Value\t" + names + "\n" + "1\n" * n

    start = time.perf_counter()
    for n in (4000, 16000):
        with pytest.raises(LvmError, match="line 7: the row has 1 cells"):
            parse_lvm(build(n))
    assert time.perf_counter() - start < 2.0


def test_a_long_segment_argument_is_not_echoed(cli: list[str], tmp_path: Path) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(format_lvm({"V": [1.0]}).encode("ascii"))
    result = run(cli, "dump", str(path), "--segment", "9" * 5000)
    assert result.returncode == 2
    assert len(result.stderr) < 600
    assert "not a segment number" in result.stderr

"""Contracts from the second adversarial review: header ends, quiet output, exact input."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from _clirun import run

from lvmio import Channel, LvmError, Segment, format_lvm, parse_lvm, read_lvm
from lvmio._cli import main

HEAD = "LabVIEW Measurement\t\nSeparator\tTab\n***End_of_Header***\t\n\n"


def _seg(value: float) -> str:
    return f"Channels\t1\n***End_of_Header***\t\nX_Value\tV\tComment\n0\t{value}\n\n"


@pytest.mark.parametrize(
    "text",
    [
        HEAD + "Channels\t1\nX_Value\tV\n0\t1\n\n" + _seg(2),
        HEAD + _seg(1) + "LabVIEW Measurement\t\nOperator\tx\n\n" + _seg(2) + _seg(3),
        HEAD + _seg(1) + "LabVIEW Measurement\t\nOperator\tx\n",
    ],
)
def test_a_header_block_without_its_end_marker_is_refused(text: str) -> None:
    with pytest.raises(LvmError, match=r"has no \*\*\*End_of_Header\*\*\* line"):
        parse_lvm(text)


def test_a_closed_standard_output_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(format_lvm({"V": [1.0, 2.0]}).encode("ascii"))
    monkeypatch.setattr(sys, "stdout", None)
    for command in (
        ["dump", str(path)],
        ["dump", str(path), "--format", "json"],
        ["channels", str(path)],
    ):
        assert main(command) == 0


def test_a_date_or_time_needs_a_channel_to_be_written_in() -> None:
    for kwargs in ({"date": "d"}, {"time": "t"}):
        with pytest.raises(ValueError, match="needs at least one channel"):
            format_lvm(Segment([], **kwargs))
    assert parse_lvm(format_lvm(Segment([Channel("V", [])], date="d"))).segments[0].date == "d"


def test_a_long_encoding_name_is_not_echoed(tmp_path: Path) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(b"\xff\xfe")
    name = "utf" + "-" * 5000 + "8"
    with pytest.raises(LvmError) as info:
        read_lvm(path, encoding=name)
    assert len(str(info.value)) < 120


class _Odd(str):
    def removeprefix(self, prefix: str) -> list[str]:  # type: ignore[override]
        return []


def test_parse_lvm_reads_a_str_subclass_as_plain_text() -> None:
    assert parse_lvm(_Odd(format_lvm({"V": [1.5]}))).segments[0]["V"].data == [1.5]


def test_the_declared_separator_is_the_one_used_and_reported() -> None:
    text = format_lvm({"V": [1.5]}, separator="Comma")
    for variant in ("  Separator,Comma", "Separator,Comma,Tab"):
        lvm = parse_lvm(text.replace("Separator,Comma", variant))
        assert lvm.separator == "Comma"
        assert lvm.segments[0]["V"].data == [1.5]
    both = text.replace("Decimal_Separator,.", "Decimal_Separator,,")
    with pytest.raises(LvmError, match="both the separator and the decimal separator"):
        parse_lvm(both)


def test_a_double_dash_segment_is_refused_plainly(cli: list[str], tmp_path: Path) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(format_lvm({"V": [1.0]}).encode("ascii"))
    result = run(cli, "dump", str(path), "--segment=--5")
    assert result.returncode == 2
    assert "not a segment number" in result.stderr


def test_memoryview_samples_are_refused_and_numpy_precision_is_accepted() -> None:
    with pytest.raises(TypeError, match="ordered iterable"):
        format_lvm({"V": memoryview(b"ab")})
    np = pytest.importorskip("numpy")
    assert "1.500\r\n" in format_lvm({"V": [1.5]}, precision=np.int64(3))

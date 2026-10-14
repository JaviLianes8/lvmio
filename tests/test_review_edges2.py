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


@pytest.mark.parametrize(
    "text",
    [
        "LabVIEW Measurement\t\nOperator\tana\n\nChannels\t1\n***End_of_Header***\t\n"
        "\nChannels\t1\n***End_of_Header***\t\nX_Value\tV\n0\t1.5\n",
        "LabVIEW Measurement\t\n\n***End_of_Header***\t\n\n" + _seg(1),
    ],
)
def test_the_file_header_must_end_before_a_blank_line(text: str) -> None:
    with pytest.raises(LvmError, match=r"file header has no .* line before a blank line"):
        parse_lvm(text)


def test_unknown_and_unusable_encodings_get_short_messages(tmp_path: Path) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(format_lvm({"V": [1.0]}).encode("ascii"))
    for call in (
        lambda: read_lvm(path, encoding="x" * 100_000),
        lambda: format_and_write(tmp_path, "q" * 100_000),
    ):
        with pytest.raises(LookupError) as info:
            call()
        assert len(str(info.value)) < 120
    with pytest.raises(ValueError) as refused:
        format_and_write(tmp_path, "ascii" + "-" * 5000, operator="Jos" + chr(0xE9))
    assert len(str(refused.value)) < 160
    with pytest.raises(LvmError, match=r"^not undefined text$"):
        read_lvm(path, encoding="undefined")


def format_and_write(folder: Path, encoding: str, operator: str = "lab") -> None:
    from lvmio import write_lvm

    write_lvm(folder / "w.lvm", {"V": [1.0]}, operator=operator, encoding=encoding)


def test_a_stray_header_line_between_rows_is_refused() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nX_Value\tV\n0\t1\nSamples\t5\n"
    with pytest.raises(LvmError, match="line 8: not a number: 'Samples'"):
        parse_lvm(text)


def test_messages_stay_short_for_unprintable_text() -> None:
    with pytest.raises(LvmError) as info:
        parse_lvm(chr(0xE0001) * 1000)
    assert len(str(info.value)) < 140


@pytest.mark.parametrize(
    ("encoding", "error"),
    [(chr(0xD800), LookupError), ("utf" + chr(0) + "8", LookupError), (5, TypeError)],
)
def test_odd_encoding_arguments_raise_documented_errors(
    encoding: object, error: type[Exception], tmp_path: Path
) -> None:
    path = tmp_path / "a.lvm"
    path.write_bytes(format_lvm({"V": [1.0]}).encode("ascii"))
    with pytest.raises(error):
        read_lvm(path, encoding=encoding)  # type: ignore[arg-type]

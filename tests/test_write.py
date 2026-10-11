from pathlib import Path

import pytest

from lvmio import Channel, LvmFile, Segment, read_lvm, write_lvm


def _file() -> LvmFile:
    channels = [
        Channel("Voltage", [1.0, 2.0, 3.0], unit="V"),
        Channel("Current", [0.5, 0.25, 0.125], unit="A"),
    ]
    return LvmFile(segments=[Segment(channels)], operator="lab")


def test_header_fields_are_written(tmp_path: Path) -> None:
    out = tmp_path / "m.lvm"
    write_lvm(out, _file(), date="2026/10/11", time="12:00:00")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("LabVIEW Measurement\t")
    assert "Separator\tTab" in text
    assert "Decimal_Separator\t." in text
    assert "X_Columns\tOne" in text
    assert "Operator\tlab" in text
    assert "Date\t2026/10/11" in text
    assert "***End_of_Header***" in text


def test_channel_names_and_comment_column(tmp_path: Path) -> None:
    out = tmp_path / "m.lvm"
    write_lvm(out, _file())
    header = next(line for line in out.read_text().splitlines() if line.startswith("X_Value"))
    assert header.split("\t") == ["X_Value", "Voltage", "Current", "Comment"]


def test_decimal_formatting_uses_precision(tmp_path: Path) -> None:
    out = tmp_path / "m.lvm"
    write_lvm(out, [Channel("A", [1.5])], precision=3)
    rows = [line for line in out.read_text().splitlines() if line and line[0].isdigit()]
    assert rows[-1].split("\t") == ["0.000", "1.500"]


def test_comma_delimiter_round_trips(tmp_path: Path) -> None:
    out = tmp_path / "m.lvm"
    write_lvm(out, _file(), separator="Comma")
    text = out.read_text(encoding="utf-8")
    assert "Separator,Comma" in text
    back = read_lvm(out)
    assert back.separator == "Comma"
    assert back.segments[0].channels[0].data == [1.0, 2.0, 3.0]


def test_mapping_input_builds_one_channel_each(tmp_path: Path) -> None:
    out = tmp_path / "m.lvm"
    write_lvm(out, {"x": [1.0, 2.0], "y": [3.0, 4.0]})
    back = read_lvm(out)
    assert [c.name for c in back.segments[0].channels] == ["x", "y"]


def test_rejects_unsupported_input(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        write_lvm(tmp_path / "m.lvm", 42)  # type: ignore[arg-type]

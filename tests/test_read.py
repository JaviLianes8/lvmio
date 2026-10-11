from pathlib import Path

import pytest

from lvmio import Channel, LvmFile, Segment, read_lvm, write_lvm

SAMPLE = "\r\n".join(
    [
        "LabVIEW Measurement\t",
        "Writer_Version\t2",
        "Reader_Version\t2",
        "Separator\tTab",
        "Decimal_Separator\t.",
        "Multi_Headings\tNo",
        "X_Columns\tOne",
        "Time_Pref\tRelative",
        "Operator\tjane",
        "Date\t2026/10/11",
        "Time\t09:30:00",
        "***End_of_Header***\t",
        "",
        "Channels\t2",
        "Samples\t3\t3",
        "Y_Unit_Label\tV\tA",
        "X_Dimension\tTime\tTime",
        "X0\t0.000000\t0.000000",
        "Delta_X\t0.100000\t0.100000",
        "***End_of_Header***\t",
        "X_Value\tVoltage\tCurrent\tComment",
        "0.000000\t1.000000\t4.000000",
        "0.100000\t2.000000\t5.000000",
        "0.200000\t3.000000\t6.000000",
        "",
    ]
)


def test_parses_minimal_known_sample(tmp_path: Path) -> None:
    path = tmp_path / "s.lvm"
    path.write_text(SAMPLE, encoding="utf-8", newline="")
    lvm = read_lvm(path)
    assert lvm.operator == "jane"
    assert lvm.x_columns == "One"
    assert len(lvm.segments) == 1
    channels = lvm.segments[0].channels
    assert [c.name for c in channels] == ["Voltage", "Current"]
    assert channels[0].data == [1.0, 2.0, 3.0]
    assert channels[1].data == [4.0, 5.0, 6.0]
    assert channels[0].unit == "V"
    assert channels[0].delta_x == 0.1


def test_round_trip_preserves_values(tmp_path: Path) -> None:
    out = tmp_path / "r.lvm"
    channels = [
        Channel("Signal", [1.0, 2.5, 3.25], unit="V", delta_x=0.5),
        Channel("Noise", [0.0, -1.0, 2.0], unit="V", delta_x=0.5),
    ]
    original = LvmFile(segments=[Segment(channels)], operator="rig")
    write_lvm(out, original)
    back = read_lvm(out)
    assert back.operator == "rig"
    assert [c.data for c in back.segments[0].channels] == [[1.0, 2.5, 3.25], [0.0, -1.0, 2.0]]
    assert back.segments[0].channels[0].delta_x == 0.5


def test_multiple_segments_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "multi.lvm"
    first = Segment([Channel("A", [1.0, 2.0])])
    second = Segment([Channel("B", [3.0, 4.0, 5.0])])
    write_lvm(out, LvmFile(segments=[first, second]))
    assert "Multi_Headings\tYes" in out.read_text(encoding="utf-8")
    back = read_lvm(out)
    assert len(back.segments) == 2
    assert back.segments[1].channels[0].data == [3.0, 4.0, 5.0]


def test_no_x_column_mode(tmp_path: Path) -> None:
    out = tmp_path / "nox.lvm"
    write_lvm(out, LvmFile(segments=[Segment([Channel("A", [7.0, 8.0])])], x_columns="No"))
    text = out.read_text(encoding="utf-8")
    assert "X_Columns\tNo" in text
    back = read_lvm(out)
    assert back.segments[0].channels[0].data == [7.0, 8.0]


def test_rejects_foreign_file(tmp_path: Path) -> None:
    path = tmp_path / "bad.lvm"
    path.write_text("not an lvm file\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_lvm(path)
